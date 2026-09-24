"""Stream the ``market_stats`` channel: a price series per market, for charts.

The history arrives in the join reply (``channel.reply["markets"]``).
Afterwards ``market_stats`` pushes the buckets that changed (upsert by
``timestamp_us``) and ``market_stats_snapshot`` replaces a series.
``price_percent`` is a percent of the market's ``max_price``, not money.
``request_series`` fetches another range without changing what streams.

Run:
    python ws_market_stats.py
    python ws_market_stats.py --seconds 60
"""

import asyncio

from demo_config import listen, make_async_client, open_market_ids, seconds_arg


def show(msg) -> str:
    points = msg.payload["points"]
    last = points[-1] if points else None
    return f"{msg.payload['market_id']}  {len(points)} bucket(s)  last {last}"


async def main(seconds: float) -> None:
    async with make_async_client() as client:
        ids = await open_market_ids(client, 3)
        async with client.websocket() as ws:
            stats = await ws.market_stats(ids, range="week")
            print(f"Joined market_stats, range {stats.reply['range']}")
            for series in stats.reply["markets"]:
                print(f"  {series['market_id']}: {len(series['points'])} point(s) of history")
            day = await stats.request_series(ids[:1], range="day")
            print(f"  request_series(day): {len(day['markets'][0]['points'])} point(s)")
            await listen(stats, seconds, show)


if __name__ == "__main__":
    asyncio.run(main(seconds_arg(20.0, __doc__.splitlines()[0])))
