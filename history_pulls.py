"""History pulls: orders, fills and settlements, one page at a time.

Every list call returns a ``Page``: iterate it like a list, and pass
``page.cursor`` back for the next page (``None`` on the last one). The
``iter_*`` methods follow the cursor for you. Useful for
reconciliation, end-of-session reports and tax export.

Amounts are dollar strings and contract counts are quantity strings,
printed as the API sends them.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python history_pulls.py
"""

from itertools import islice

from demo_config import make_client

PAGE_LIMIT = 10


def main() -> None:
    with make_client() as client:
        orders = client.orders(limit=PAGE_LIMIT)
        print(f"Orders: {len(orders)} on this page (more: {orders.has_more})")
        for o in orders:
            print(
                f"  {o.id}  {o.action:<4} {o.filled}/{o.quantity} @ {o.price or 'market'}  "
                f"{o.status:<10} {o.time}"
            )

        if orders.cursor:
            older = client.orders(limit=PAGE_LIMIT, cursor=orders.cursor)
            print(f"  next page: {len(older)} more")

        fills = client.fills(limit=PAGE_LIMIT)
        print(f"\nFills: {len(fills)} on this page")
        for f in fills:
            print(
                f"  {f.trade_id}  {f.action:<4} {f.filled} @ {f.price}  "
                f"fee {f.total_fee}  {f.status:<8} {f.time}"
            )

        print("\nSettlements (first 25 across pages)")
        for s in islice(client.iter_settlements(limit=PAGE_LIMIT), 25):
            print(
                f"  {s.id}  {s.type:<13} qty {s.quantity}  "
                f"{s.opening_price} -> {s.closing_price}  pnl {s.realized_pnl}  fee {s.fee}"
            )


if __name__ == "__main__":
    main()
