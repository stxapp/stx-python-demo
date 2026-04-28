"""History pulls — orders, trades, settlements with Page semantics.

The three history ops all return ``Page[T]`` — iterable + ``.count``
for the server total. Useful for reconciliation, end-of-session
reports, and tax export.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python history_pulls.py

Note: monetary fields on the wire are integer cents — divide by 100
to display dollars.
"""
from __future__ import annotations  # PEP 604 union syntax in helpers (3.9 compat)

from stx import STX, Selection


PAGE_LIMIT = 10


def _fmt_cents(c: int | None) -> str:
    return "  —" if c is None else f"${c / 100:>8,.2f}"


def main() -> None:
    with STX(region="ontario", env="staging") as client:
        client.login(params={})

        # ---- Orders ---------------------------------------------------
        # ``client.orders`` returns Page[Order]; flat Selection auto-wraps
        # under the inner list field, no envelope boilerplate.
        orders = client.orders(
            params={"pagination": {"page": 0, "limit": PAGE_LIMIT}},
            selections=Selection(
                "id", "market_id", "status", "action",
                "price", "quantity", "filled", "time",
            ),
        )
        print(f"Orders — showing {len(orders)} of {orders.count}")
        for o in orders:
            print(
                f"  {(o.id or '—'):<14} {(o.market_id or '—'):<14} "
                f"{(o.action or '—'):<5} "
                f"qty={o.quantity or 0:>5}/{o.filled or 0:<5}  "
                f"px={_fmt_cents(o.price)}  "
                f"{(o.status or '—'):<10} {o.time or ''}"
            )

        # ---- Trades ---------------------------------------------------
        # Trade.filled is the executed quantity (NOT `quantity`).
        trades = client.trades(
            params={"pagination": {"page": 0, "limit": PAGE_LIMIT}},
            selections=Selection(
                "id", "market_id", "action", "price", "filled",
                "premium", "time",
            ),
        )
        print(f"\nTrades — showing {len(trades)} of {trades.count}")
        for t in trades:
            print(
                f"  {(t.id or '—'):<14} {(t.market_id or '—'):<14} "
                f"{(t.action or '—'):<5} "
                f"filled={t.filled or 0:>5}  "
                f"px={_fmt_cents(t.price)}  "
                f"premium={_fmt_cents(t.premium)}  {t.time or ''}"
            )

        # ---- Settlements ----------------------------------------------
        # `inserted_at_iso` is the human-readable ISO timestamp;
        # `realized_pnl` is profit/loss net of fees.
        settlements = client.settlements(
            params={"pagination": {"page": 0, "limit": PAGE_LIMIT}},
            selections=Selection(
                "id", "market_id", "type", "quantity",
                "realized_pnl", "fee", "inserted_at_iso",
            ),
        )
        print(f"\nSettlements — showing {len(settlements)} of {settlements.count}")
        for s in settlements:
            print(
                f"  {(s.id or '—'):<14} {(s.market_id or '—'):<14} "
                f"{(s.type or '—'):<10} "
                f"qty={s.quantity or 0:>5}  "
                f"pnl={_fmt_cents(s.realized_pnl)}  "
                f"fee={_fmt_cents(s.fee)}  {s.inserted_at_iso or ''}"
            )


if __name__ == "__main__":
    main()
