"""Stream the ``market_updates`` channel: changes for the markets you watch.

Joining alone sends nothing; ``watch`` names the markets. Each
``updated`` push carries the market id, timestamps and the changed
fields; ``created`` carries the whole market. Prices arrive in cents on
the wire and the SDK converts them to dollar strings. The SDK re-sends
your watches after a reconnect.

Run:
    python ws_market_updates.py
    python ws_market_updates.py --seconds 60
"""

import asyncio

from demo_config import listen, make_async_client, open_market_ids, seconds_arg


def show(msg) -> str:
    p = msg.payload
    changed = {
        k: v for k, v in p.items() if k not in ("market_id", "id", "timestamp", "unix_timestamp")
    }
    return f"{p['market_id']} {changed}"[:220]


async def main(seconds: float) -> None:
    async with make_async_client() as client:
        ids = await open_market_ids(client, 10)
        async with client.websocket() as ws:
            updates = await ws.market_updates()
            reply = await updates.watch(ids)
            print(f"Watching {len(reply['subscriptions']['watches'])} market(s)")
            await listen(updates, seconds, show)


if __name__ == "__main__":
    asyncio.run(main(seconds_arg(20.0, __doc__.splitlines()[0])))
