"""Stream the ``ticker`` channel: a price summary whenever a market moves.

Pushes ``ticker`` when a market's last trade, top of book, volume or
open interest changes. Filter by ``sports`` and ``competitions`` (exact
names), and change them later with ``select_filters``. There is no
snapshot: read the starting state from ``markets()``.

Run:
    python ws_ticker.py
    python ws_ticker.py --seconds 60
"""

import asyncio

from demo_config import listen, make_async_client, seconds_arg


def show(msg) -> str:
    p = msg.payload
    return (
        f"{p['market_symbol']}  last {p['last_traded_price']}  "
        f"bid {p['best_bid']} x {p['best_bid_quantity']}  offer {p['best_offer']} x "
        f"{p['best_offer_quantity']}  "
        f"vol {p['total_volume']}"
    )


async def main(seconds: float) -> None:
    async with make_async_client() as client:
        async with client.websocket() as ws:
            ticker = await ws.ticker()
            print(f"Joined ticker: {ticker.reply}")
            await listen(ticker, seconds, show)


if __name__ == "__main__":
    asyncio.run(main(seconds_arg(20.0, __doc__.splitlines()[0])))
