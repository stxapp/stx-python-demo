"""Stream your ``balances`` channel: balance and fee summary, then changes.

``balances`` on join; ``update`` when the balance changes (orders,
fills, settlements, payments; not price moves) and ``payment_update``
for payments. Amounts are dollar strings. ``account_id=`` picks another
account you own.

Run:
    python ws_balances.py
    python ws_balances.py --seconds 60
"""

import asyncio

from demo_config import listen, make_async_client, seconds_arg


def show(msg) -> str:
    p = msg.payload
    if msg.event == "payment_update":
        return f"payment {p['type']} {p['amount']} {p['status']}"
    return f"available {p['available_balance']}  cash {p['account_balance']}"


async def main(seconds: float) -> None:
    async with make_async_client() as client:
        async with client.websocket() as ws:
            balances = await ws.balances()
            print(f"Joined {balances.topic}: {balances.reply}")
            b = (await balances.wait_snapshot())["balances"]
            print(f"Available {b['available_balance']}  cash {b['account_balance']}")
            print(f"Liabilities: buy {b['buy_order_liability']}  sell {b['sell_order_liability']}")
            print(
                f"Fees: {b['fee_schedule']} taker {b['taker_factor']} maker {b['maker_factor']}  "
                f"tier {b['loyalty_tier']}"
            )
            await balances.next(timeout=5)
            await listen(balances, seconds, show)


if __name__ == "__main__":
    asyncio.run(main(seconds_arg(20.0, __doc__.splitlines()[0])))
