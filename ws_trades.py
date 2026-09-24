"""Stream the public ``trades`` channel: every execution on the exchange, anonymised.

``action`` is the taker's side. Filter by ``market_ids`` and
``event_ids``. This is everyone's trades; your own executions are the
``fills`` channel (``ws_fills.py``).

Run:
    python ws_trades.py
    python ws_trades.py --seconds 60
"""

import asyncio

from demo_config import listen, make_async_client, seconds_arg


def show(msg) -> str:
    p = msg.payload
    return f"{p['market_symbol']}  taker {p['action']:<4} {p['quantity']} @ {p['price']}"


async def main(seconds: float) -> None:
    async with make_async_client() as client:
        async with client.websocket() as ws:
            trades = await ws.trades()
            print(f"Joined trades: {trades.reply}")
            await listen(trades, seconds, show)


if __name__ == "__main__":
    asyncio.run(main(seconds_arg(20.0, __doc__.splitlines()[0])))
