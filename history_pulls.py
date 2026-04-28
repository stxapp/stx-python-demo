"""History pulls — orders, trades, settlements with Page semantics.

The three history ops all return ``Page[T]`` — iterable + ``.count``
for the server total. Useful for reconciliation, end-of-session
reports, and tax export.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python history_pulls.py
"""
from stx import STX, Selection


PAGE_LIMIT = 10


def main() -> None:
    with STX(region="ontario", env="staging") as client:
        client.login(params={})

        # ---- Orders ---------------------------------------------------
        # ``client.orders`` returns Page[Order]; flat Selection auto-wraps
        # under the inner list field, no envelope boilerplate.
        orders = client.orders(
            params={"pagination": {"page": 0, "limit": PAGE_LIMIT}},
            selections=Selection(
                "id", "market_id", "status", "action", "order_type",
                "price", "quantity", "created_at",
            ),
        )
        print(f"Orders — showing {len(orders)} of {orders.count}")
        for o in orders:
            print(
                f"  {o.id or '—':<12} {o.market_id or '—':<20} "
                f"{o.action or '—':<5} {o.order_type or '—':<7} "
                f"qty={o.quantity or 0:>6}  px={o.price or 0:>5}  "
                f"{o.status or '—'}  {o.created_at or ''}"
            )

        # ---- Trades ---------------------------------------------------
        trades = client.trades(
            params={"pagination": {"page": 0, "limit": PAGE_LIMIT}},
            selections=Selection(
                "id", "market_id", "action", "price", "quantity", "time"
            ),
        )
        print(f"\nTrades — showing {len(trades)} of {trades.count}")
        for t in trades:
            print(
                f"  {t.id or '—':<12} {t.market_id or '—':<20} "
                f"{t.action or '—':<5} qty={t.quantity or 0:>6}  "
                f"px={t.price or 0:>5}  {t.time or ''}"
            )

        # ---- Settlements ----------------------------------------------
        settlements = client.settlements(
            params={"pagination": {"page": 0, "limit": PAGE_LIMIT}},
            selections=Selection("id", "market_id", "amount", "time"),
        )
        print(f"\nSettlements — showing {len(settlements)} of {settlements.count}")
        for s in settlements:
            print(
                f"  {s.id or '—':<12} {s.market_id or '—':<20} "
                f"amount={s.amount or 0:>+10.2f}  {s.time or ''}"
            )


if __name__ == "__main__":
    main()
