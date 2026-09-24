"""Markets channel: single-market live order book.

Pins to one ``market_id`` and renders its top-of-book bids / offers as
they update. The ``markets`` channel has no native ``market_id`` filter
(only ``fields`` / ``rule_filters`` / ``message_types``), so we narrow
server-side to the bids/offers fields and filter client-side for the
target market.

Set ``STX_MARKET_ID`` in the environment to pin a specific market, or leave it
unset and the script auto-discovers an OPEN market via the HTTP API.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    # Optional: pin a specific market
    # export STX_MARKET_ID="..."
    python ws_markets_order_book.py
"""
import asyncio
import os
import sys
from collections import Counter
from datetime import datetime

from stx import STX, Selection
from stx.enums import Channels

from demo_config import make_client, make_ws

LISTEN_WINDOW_SECONDS = 30
DEPTH = 5


def _hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _ladder(levels, side: str) -> str:
    if not levels:
        return f"  {side}: (empty)"
    rows = []
    for lvl in (levels or [])[:DEPTH]:
        if isinstance(lvl, dict):
            price = lvl.get("price")
            size = lvl.get("quantity") or lvl.get("size")
            rows.append(f"    {price!s:>8}  x  {size!s}")
    return f"  {side}:\n" + "\n".join(rows)


def _resolve_market_id(client: STX) -> str:
    """Use the env override if set, otherwise grab the first OPEN market."""
    override = os.getenv("STX_MARKET_ID")
    if override:
        return override
    page = client.markets(
        status=["OPEN"],
        limit=1,
        selections=Selection("market_id", "title"),
    )
    if not len(page):
        raise SystemExit(
            "No OPEN markets on this environment. Set STX_MARKET_ID, or try "
            "again when events are in play."
        )
    m = next(iter(page))
    print(f"Auto-discovered market_id={m.market_id} ({m.title!r})")
    return m.market_id


async def stream() -> None:
    client = make_client()
    client.login()
    target = _resolve_market_id(client)

    events: Counter = Counter()
    matched = 0

    async def on_msg(msg) -> None:
        nonlocal matched
        events[msg.event] += 1
        if msg.is_join_reply:
            print(f"  [{_hms()}] join-reply  watching market_id={target!r}")
            return
        p = msg.payload or {}
        if p.get("market_id") != target:
            return
        matched += 1
        print(f"\n  [{_hms()}] === update #{matched} @ {p.get('timestamp')} ===")
        print(_ladder(p.get("bids"), "bids"))
        print(_ladder(p.get("offers"), "offers"))

    async with make_ws() as ws:
        await ws.join(
            Channels.MARKETS,
            on_message=on_msg,
            join_params={"fields": ["bids", "offers"]},
        )
        print(
            f"Tracking order book for market_id={target!r} for "
            f"{LISTEN_WINDOW_SECONDS}s..."
        )
        try:
            await asyncio.wait_for(asyncio.Event().wait(), LISTEN_WINDOW_SECONDS)
        except asyncio.TimeoutError:
            pass

    print(
        f"\nReceived {events.get('market_updated', 0)} market_updated frames "
        f"in {LISTEN_WINDOW_SECONDS}s; {matched} matched the target market."
    )
    if matched == 0:
        print("  (no ticks for this market; try a different STX_MARKET_ID, "
              "or try again when events are in play)")


def main() -> None:
    try:
        asyncio.run(stream())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
