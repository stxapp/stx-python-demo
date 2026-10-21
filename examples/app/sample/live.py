"""Live data for the browser, relayed over server-sent events.

STX sockets authenticate with a token in a header on the WebSocket
handshake. A browser cannot set that header, and must never hold a token
anyway, so this server opens the STX socket and relays what it needs:

* ``GET /live/market/{id}``: the order book and ticker for one market, on
  the app's own token (``market_data``). No member involved.
* ``GET /live/account``: the signed-in member's balance, open orders,
  fills and positions, from ``ws.account_view()`` on their token.

One STX socket per open page keeps the code short; a busy app would share
one socket per member or market.

When the page closes, the server cancels the stream, and ``closing()``
makes sure the STX socket still closes all the way.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any, Optional

import anyio
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from stx import oauth

from sample.context import ctx, current_user, is_connected, member_client, member_key

router = APIRouter()
log = logging.getLogger("sample.live")

KEEPALIVE_SECONDS = 15
BOOK_DEPTH = 5

# The queues of open account feeds per member, so unlinking can end them.
_account_feeds: dict[str, set["asyncio.Queue[Optional[str]]"]] = {}


def sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def stream(gen: AsyncIterator[str]) -> StreamingResponse:
    return StreamingResponse(gen, media_type="text/event-stream", headers={"Cache-Control": "no-store"})


@asynccontextmanager
async def closing(resource: Any) -> AsyncIterator[Any]:
    """Close ``resource`` on the way out, even while the stream is being
    cancelled: a cancelled ``close()`` would leave the STX socket open."""
    try:
        yield resource
    finally:
        with anyio.CancelScope(shield=True):
            await resource.close()


async def relay(queue: "asyncio.Queue[Optional[str]]") -> AsyncIterator[str]:
    """Yield queued events until a None, with a keep-alive comment when quiet."""
    while True:
        try:
            item = await asyncio.wait_for(queue.get(), KEEPALIVE_SECONDS)
        except asyncio.TimeoutError:
            yield ": keep-alive\n\n"
            continue
        if item is None:
            return
        yield item


# ---- market data, on the app token --------------------------------------


def book_side(levels: Any) -> list[dict[str, str]]:
    return [{"price": lv.get("price"), "quantity": lv.get("quantity")} for lv in (levels or [])[:BOOK_DEPTH]]


@router.get("/live/market/{market_id}")
async def market_feed(request: Request, market_id: str, sport: str = ""):
    catalog = ctx(request).catalog
    if catalog is None:
        return JSONResponse({"error": "not_available"}, status_code=501)

    async def events() -> AsyncIterator[str]:
        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

        def on_book(msg) -> None:
            # Each `book` push is the whole book for one market: replace, don't merge.
            p = msg.payload
            queue.put_nowait(sse("book", {"bids": book_side(p.get("bids")), "offers": book_side(p.get("offers"))}))

        def on_ticker(msg) -> None:
            p = msg.payload
            if p.get("market_id") == market_id:
                keys = ("best_bid", "best_offer", "last_traded_price", "total_volume", "timestamp")
                queue.put_nowait(sse("ticker", {k: p.get(k) for k in keys}))

        try:
            async with closing(catalog.websocket()) as ws:
                await ws.orderbook([market_id], on_message=on_book)
                # The ticker covers every market; narrow it by sport, then by id above.
                await ws.ticker(sports=[sport] if sport else None, on_message=on_ticker)
                yield sse("joined", {"market_id": market_id})
                async for chunk in relay(queue):
                    yield chunk
        finally:
            log.info("closed the market feed for %s", market_id)

    return stream(events())


# ---- the member's account, on their token --------------------------------


def account_state(view: Any) -> dict[str, Any]:
    """The parts of the live view the dashboard shows."""
    balance = view.balance or {}
    return {
        "available_balance": balance.get("available_balance"),
        "account_balance": balance.get("account_balance"),
        "open_orders": [
            {k: o.get(k) for k in ("id", "market_id", "action", "price", "quantity", "filled", "status")}
            for o in view.open_orders
        ],
        "positions": len([p for p in view.positions if Decimal(str(p.get("position") or 0)) != 0]),
        "fills": len(view.fills),
    }


@router.get("/live/account")
async def account_feed(request: Request):
    user = current_user(request)
    if not is_connected(request, user):
        return JSONResponse({"error": "not_connected"}, status_code=401)
    key = member_key(user)
    queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

    async def events() -> AsyncIterator[str]:
        _account_feeds.setdefault(key, set()).add(queue)
        try:
            async with closing(member_client(request, user)) as member, closing(member.websocket()) as ws:

                def on_change(change) -> None:
                    if not change.snapshot:
                        queue.put_nowait(
                            sse("change", {"kind": change.kind, "event": change.event, **account_state(change.view)})
                        )

                view = await ws.account_view(on_change=on_change)
                yield sse("snapshot", account_state(view))
                async for chunk in relay(queue):
                    yield chunk
            yield sse("ended", {"reason": "disconnected"})
        except oauth.STXGrantRevokedException:
            yield sse("ended", {"reason": "grant_revoked"})
        finally:
            _account_feeds.get(key, set()).discard(queue)
            log.info("closed the account feed for member %s", key)

    return stream(events())


async def close_account_feeds(request: Request, user: dict[str, Any]) -> None:
    """End this member's live feeds now: nothing should stream on a grant
    that is about to be revoked."""
    for queue in list(_account_feeds.get(member_key(user), ())):
        queue.put_nowait(None)
