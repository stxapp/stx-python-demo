"""Event-driven bot pattern: ``AsyncSTX`` + ``STXWebSocket`` together.

Wires up the canonical pair: a WebSocket pushing live market frames,
an async HTTP client ready to react. When a market update arrives, we
look up the market's full state via HTTP. That's the shape most
trading bots use: WS for low-latency events, HTTP for queries and
order placement.

Both clients sign their own traffic with the same API key, so there
is nothing to log in to first. The markets channel is a broadcast and
needs no user id.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python async_with_ws.py
"""
import asyncio
import sys

from stx import Selection
from stx.enums import Channels

from demo_config import make_async_client, make_ws

LISTEN_WINDOW_SECONDS = 20
LOOKUP_AT_MOST = 3   # Cap the HTTP fan-out so the demo stays bounded.


async def main() -> None:
    async with make_async_client() as client:
        seen_market_ids: set[str] = set()
        lookup_count = 0

        async def on_market(msg) -> None:
            nonlocal lookup_count
            if msg.is_reply:
                return
            # Frames are dicts keyed by market_id; take the first new one.
            mid = next(
                (k for k in (msg.payload or {}) if k not in seen_market_ids), None
            )
            if not mid or lookup_count >= LOOKUP_AT_MOST:
                return
            seen_market_ids.add(mid)
            lookup_count += 1
            # WS event → HTTP lookup. In a real bot this is where you'd
            # decide whether to quote, hedge, or no-op.
            page = await client.markets(
                market_ids=[mid],
                selections=Selection("market_id", "title", "price", "probability"),
            )
            if len(page):
                m = page[0]
                print(
                    f"  WS update on {mid} → HTTP says: "
                    f"{m.title!r} px={m.price} prob={m.probability}"
                )

        async with make_ws() as ws:
            await ws.join(Channels.MARKETS, on_message=on_market)
            print(
                f"Subscribed. Looking up the first {LOOKUP_AT_MOST} unique "
                f"markets that publish, or for {LISTEN_WINDOW_SECONDS}s, "
                "whichever comes first."
            )
            try:
                await asyncio.wait_for(asyncio.Event().wait(), LISTEN_WINDOW_SECONDS)
            except asyncio.TimeoutError:
                pass

        print(
            f"\nLooked up {lookup_count} market(s) in response to live frames."
        )
        if lookup_count == 0:
            print(
                "  (no frames carried a market_id we could look up; the "
                "environment may be quiet when no events are in play.)"
            )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
