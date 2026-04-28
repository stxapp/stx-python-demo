"""Stream live market updates over a WebSocket.

Joins the broadcast ``Channels.MARKETS`` topic, which pushes price /
status / orderbook updates for every market on the exchange. Listens
for a fixed window, prints each frame as it arrives, then summarises.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python ws_market_stream.py

``STXWebSocket`` is async-native — Phoenix is event-driven and there's
no useful sync wrapper. From a sync codebase you call into it via
``asyncio.run(...)`` like this script does.
"""
import asyncio
import sys
from collections import Counter

from stx import STX, STXWebSocket
from stx.enums import Channels


LISTEN_WINDOW_SECONDS = 30


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

    async with STXWebSocket(region="ontario", env="staging") as ws:
        # MARKETS is a broadcast channel — no per-user scoping. The
        # `Channels` enum auto-maps to the wire topic "market_info".
        await ws.join(Channels.MARKETS, on_message=on_msg)
        print(f"Listening on Channels.MARKETS for {LISTEN_WINDOW_SECONDS}s...")
        try:
            await asyncio.wait_for(asyncio.Event().wait(), LISTEN_WINDOW_SECONDS)
        except asyncio.TimeoutError:
            pass  # timeout is the expected exit

    # Summary — useful for sanity-checking the connection works even
    # outside trading hours when the stream is quiet.
    print(f"\nReceived {len(received)} frames in {LISTEN_WINDOW_SECONDS}s:")
    for event, count in sorted(events.items(), key=lambda x: -x[1]):
        print(f"  {event:<25} {count}")
    if not received:
        print("  (no frames — dev may be quiet outside ET market hours)")


def main() -> None:
    try:
        asyncio.run(stream())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
