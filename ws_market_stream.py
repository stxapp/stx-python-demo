"""Stream live market updates over a WebSocket.

Joins the broadcast ``Channels.MARKETS`` topic, which pushes price /
probability / orderbook updates from market-wide trading activity.
Prints each frame as it arrives, then summarises by event type at the
end.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python ws_market_stream.py

What you'll see:

- During ET trading hours: a stream of ``market_update``-shaped frames
  carrying price/probability ticks for whichever markets are active.
- Outside trading hours: just the join-reply (``phx_reply``) and then
  silence — markets aren't moving, so there's nothing to broadcast.

Note: your *own* order activity (place / fill / cancel) does NOT show
up here — that goes to the per-user ``Channels.ORDERS`` channel.
See ``ws_personal_stream.py``.

``STXWebSocket`` is async-native — Phoenix is event-driven and there's
no useful sync wrapper. From a sync codebase you call into it via
``asyncio.run(...)`` like this script does.
"""
import asyncio
import sys
from collections import Counter
from datetime import datetime

from stx import STX, STXWebSocket
from stx.enums import Channels


LISTEN_WINDOW_SECONDS = 30


def _now_hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _fmt_book_side(side):
    """Render a list of {price, quantity} bid/offer entries compactly.
    Shows the top three levels and a count of any extras."""
    if not side:
        return "—"
    if not isinstance(side, list):
        return repr(side)
    levels = []
    for entry in side[:3]:
        if isinstance(entry, dict):
            px = entry.get("price")
            qty = entry.get("quantity") or entry.get("qty")
            levels.append(f"{px}@{qty}")
        else:
            levels.append(str(entry))
    rendered = ", ".join(levels)
    if len(side) > 3:
        rendered += f" (+{len(side) - 3})"
    return rendered


def _fmt_market_payload(payload):
    """Pluck the fields a trader actually wants from a market_update
    payload — id, status, bids, offers — and ignore the rest. Falls
    back to a truncated repr for control frames that don't carry a
    market shape (e.g. phx_reply)."""
    if not isinstance(payload, dict):
        return "—" if payload is None else str(payload)
    # Server keys vary slightly by event; check both camelCase and snake.
    market_id = payload.get("marketId") or payload.get("market_id") or payload.get("id")
    status = payload.get("status")
    bids = payload.get("bids")
    offers = payload.get("offers")
    # Recognise a market-shaped frame by the presence of bids/offers or a
    # market id. `status` alone isn't enough — phx_reply also carries a
    # `status: ok` and we don't want to render it as a (mostly-empty)
    # market row.
    if bids is None and offers is None and market_id is None:
        s = repr(payload)
        return s if len(s) <= 120 else s[:117] + "..."
    return (
        f"id={market_id}  status={status}  "
        f"bids=[{_fmt_book_side(bids)}]  "
        f"offers=[{_fmt_book_side(offers)}]"
    )


async def stream() -> None:
    # Seed the User singleton so the WS client picks up the JWT —
    # STXWebSocket reads the token but doesn't perform login itself.
    with STX(region="ontario", env="staging") as client:
        client.login(params={})

    received = []
    events = Counter()

    async def on_msg(msg) -> None:
        events[msg.event] += 1
        received.append(msg)
        print(f"  [{_now_hms()}] {msg.event:<20} {_fmt_market_payload(msg.payload)}")

    async with STXWebSocket(region="ontario", env="staging") as ws:
        # MARKETS is a broadcast channel — no per-user scoping. The
        # `Channels` enum auto-maps to the wire topic "market_info".
        await ws.join(Channels.MARKETS, on_message=on_msg)
        print(
            f"Listening on Channels.MARKETS for {LISTEN_WINDOW_SECONDS}s "
            f"(streaming live; summary at the end)..."
        )
        try:
            await asyncio.wait_for(asyncio.Event().wait(), LISTEN_WINDOW_SECONDS)
        except asyncio.TimeoutError:
            pass  # timeout is the expected exit

    # Summary — useful when the stream is sparse and you want a count
    # by event type at a glance.
    print(f"\nReceived {len(received)} frames in {LISTEN_WINDOW_SECONDS}s:")
    for event, count in sorted(events.items(), key=lambda x: -x[1]):
        print(f"  {event:<25} {count}")
    if not received:
        print(
            "  (no frames — dev may be quiet outside ET market hours, or "
            "the markets you'd see updates for aren't active right now)"
        )


def main() -> None:
    try:
        asyncio.run(stream())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
