"""Print your balance, positions, open orders and recent fills.

Run: python examples/portfolio.py
"""

from decimal import Decimal

from stx import STX

with STX() as client:
    me = client.me()
    print(f"Key scope: {me.scope}\n")

    # Money is in dollars, as decimal strings. available_balance is what you can
    # place orders with right now; the rest is held by open orders and positions.
    balance = client.balance()
    print(f"Balance: {balance.account_balance}  available {balance.available_balance}")

    # position is positive when you are long (you bought), negative when short.
    # Markets you have traded out of stay in the list with position 0; skip those.
    positions = [p for p in client.positions() if Decimal(p.position or "0") != 0]
    print(f"\nOpen positions: {len(positions)}")
    for p in positions:
        print(f"  {p.market_id}  {p.position}")

    orders = client.orders(status=["open", "delayed"], limit=10)
    print(f"\nOpen orders: {len(orders)}{' (more available)' if orders.has_more else ''}")
    for o in orders:
        print(f"  {o.id}  {o.action} {o.quantity} @ {o.price}  filled {o.filled}")

    fills = client.fills(limit=5)
    print(f"\nRecent fills: {len(fills)}")
    for f in fills:
        print(f"  {f.trade_id}  {f.action} {f.filled} @ {f.price}")
