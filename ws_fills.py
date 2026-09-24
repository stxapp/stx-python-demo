"""Stream your ``fills`` channel: your own executions.

``all_trades`` arrives on join with your open trades, then one ``trade``
push per execution or status change (including trades that settle or
are cancelled). ``total_fee`` is the all-in fee. The anonymous feed of
everyone's trades is the ``trades`` channel instead.

Run:
    python ws_fills.py
    python ws_fills.py --seconds 60
"""

import asyncio

from demo_config import listen, make_async_client, seconds_arg


def show(msg) -> str:
    p = msg.payload
    return (
        f"{p['id']} {p['status']:<8} {p['action']} {p['filled']} @ {p['price']} fee "
        f"{p['total_fee']}"
    )


async def main(seconds: float) -> None:
    async with make_async_client() as client:
        async with client.websocket() as ws:
            fills = await ws.fills()
            print(f"Joined {fills.topic}: {fills.reply}")
            trades = (await fills.wait_snapshot())["all_trades"]["trades"]
            print(f"Snapshot: {len(trades)} open trade(s)")
            for t in trades[:5]:
                print(
                    f"  {t['id']} {t['action']} {t['filled']} @ {t['price']} remaining "
                    f"{t['remaining']}"
                )
            await fills.next(timeout=5)
            await listen(fills, seconds, show)


if __name__ == "__main__":
    asyncio.run(main(seconds_arg(20.0, __doc__.splitlines()[0])))
