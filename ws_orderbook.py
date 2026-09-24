"""Stream the ``orderbook`` channel: the aggregated book for the markets you name.

Each ``book`` push is the full book for one market, best level first, so
replace what you hold rather than merging. ``market_ids`` is required;
``select_market_ids`` changes the set without rejoining. Levels carry
``price``, ``quantity``, ``liquidity`` and the cumulative
``total_quantity`` / ``total_liquidity``, all strings.

Run:
    python ws_orderbook.py              # five open markets, 20 s
    python ws_orderbook.py --seconds 60
"""

import asyncio

from demo_config import listen, make_async_client, open_market_ids, seconds_arg


def show(msg) -> str:
    p = msg.payload
    bid = p["bids"][0] if p["bids"] else None
    offer = p["offers"][0] if p["offers"] else None
    fmt = lambda lvl: f"{lvl['quantity']}@{lvl['price']}" if lvl else "-"  # noqa: E731
    return (
        f"{p['market_id']}  best bid {fmt(bid)}  best offer {fmt(offer)}  levels "
        f"{len(p['bids'])}/{len(p['offers'])}"
    )


async def main(seconds: float) -> None:
    async with make_async_client() as client:
        ids = await open_market_ids(client, 5)
        async with client.websocket() as ws:
            book = await ws.orderbook(ids)
            print(
                f"Joined orderbook; server applied {len(book.reply['selected_market_ids'])} "
                "market ids"
            )
            reply = await book.select_market_ids(ids[:3])
            print(f"Narrowed to {len(reply['selected_market_ids'])} with select_market_ids")
            await listen(book, seconds, show)


if __name__ == "__main__":
    asyncio.run(main(seconds_arg(20.0, __doc__.splitlines()[0])))
