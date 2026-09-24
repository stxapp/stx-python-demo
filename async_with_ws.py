"""Event-driven pattern: a WebSocket feed drives REST lookups.

The ``ticker`` channel pushes a line whenever a market's price, top of
book or volume moves. For the first few markets that move, the script
fetches the full market over REST, the way a bot reacts to an event by
reading state and deciding whether to quote. Both clients sign with the
same key; there is nothing to log in to.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python async_with_ws.py
"""

import asyncio

from demo_config import hms, make_async_client, seconds_arg

LOOKUP_AT_MOST = 3


async def main(seconds: float) -> None:
    async with make_async_client() as client:
        seen = set()
        async with client.websocket() as ws:
            ticker = await ws.ticker()
            print(
                f"Joined ticker; reacting to the first {LOOKUP_AT_MOST} markets that move in "
                f"{seconds:g}s"
            )
            loop = asyncio.get_running_loop()
            deadline = loop.time() + seconds
            while len(seen) < LOOKUP_AT_MOST and loop.time() < deadline:
                try:
                    msg = await ticker.next(timeout=deadline - loop.time())
                except asyncio.TimeoutError:
                    break
                mid = msg.payload["market_id"]
                if mid in seen:
                    continue
                seen.add(mid)
                market = await client.market(mid)
                print(
                    f"  [{hms()}] {msg.payload['market_symbol']}: last "
                    f"{msg.payload['last_traded_price']} "
                    f"-> REST: {market.title!r} status {market.status} bid "
                    f"{market.bids[0].price if market.bids else '-'}"
                )
            if not seen:
                print("  no market moved; the demo exchange can be quiet")


if __name__ == "__main__":
    asyncio.run(main(seconds_arg(20.0, __doc__.splitlines()[0])))
