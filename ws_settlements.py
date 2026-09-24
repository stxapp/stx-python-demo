"""Stream your ``settlements`` channel: a push whenever a market you hold settles.

There is no snapshot: history comes from ``client.settlements()``, which
this script prints first, then it listens for ``new_settlements``.

Run:
    python ws_settlements.py
    python ws_settlements.py --seconds 60
"""

import asyncio

from demo_config import listen, make_async_client, seconds_arg


def show(msg) -> str:
    return ", ".join(
        f"{s['type']} {s['quantity']} pnl {s['realized_pnl']}" for s in msg.payload["settlements"]
    )


async def main(seconds: float) -> None:
    async with make_async_client() as client:
        recent = await client.settlements(limit=3)
        print("Recent settlements (REST):")
        for s in recent:
            print(
                f"  {s.type:<13} {s.quantity} {s.opening_price} -> {s.closing_price} pnl "
                f"{s.realized_pnl}"
            )
        async with client.websocket() as ws:
            settlements = await ws.settlements()
            print(f"Joined {settlements.topic}: {settlements.reply}")
            await listen(settlements, seconds, show)


if __name__ == "__main__":
    asyncio.run(main(seconds_arg(20.0, __doc__.splitlines()[0])))
