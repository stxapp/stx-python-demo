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
        # Live print — what you came here to see. Truncate the payload
        # if it's chatty so the table stays readable.
        payload = repr(msg.payload)
        if len(payload) > 120:
            payload = payload[:117] + "..."
        print(f"  [{_now_hms()}] {msg.event:<20} {payload}")

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
