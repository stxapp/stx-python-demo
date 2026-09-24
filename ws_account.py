"""Stream the ``account`` channel: all of your account on one join.

Four snapshots on join (``all_orders``, ``all_trades``, ``all_positions``,
``balances``), then the same events the per-type channels push, under
the same names. Do not also join ``orders`` or ``fills`` on the same
socket (you would get everything twice), and use ``orders`` instead if
you need cancel-on-disconnect.

Run:
    python ws_account.py
    python ws_account.py --seconds 60
"""

import asyncio

from demo_config import listen, make_async_client, seconds_arg


def show(msg) -> str:
    return str(msg.payload)[:200]


async def main(seconds: float) -> None:
    async with make_async_client() as client:
        async with client.websocket() as ws:
            account = await ws.account()
            print(f"Joined {account.topic}: {account.reply}")
            snap = await account.wait_snapshot()
            print(f"  orders:    {len(snap['all_orders']['orders'])}")
            print(f"  trades:    {len(snap['all_trades']['trades'])}")
            print(f"  positions: {len(snap['all_positions']['positions'])}")
            print(f"  available: {snap['balances']['available_balance']}")
            for _ in range(4):  # drain the four snapshot messages
                await account.next(timeout=5)
            await listen(account, seconds, show)


if __name__ == "__main__":
    asyncio.run(main(seconds_arg(20.0, __doc__.splitlines()[0])))
