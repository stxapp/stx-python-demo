"""Account overview — balances, loyalty tier, per-market positions.

Read-only snapshot of everything the SDK exposes about your STX
account. Useful as a first authenticated call after login (proves
auth works) and as a starting point for portfolio-tracking scripts.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python account_overview.py

Note: monetary fields on the wire are integer cents — divide by 100
to display dollars.
"""
from datetime import datetime, timezone

from stx import STX, Selection


def _fmt_cents(c: int | None) -> str:
    if c is None:
        return "  —"
    return f"${c / 100:>10,.2f}"


def _fmt_us(us: int | None) -> str:
    """Render a UNIX-microseconds timestamp as a short ISO date."""
    if not us:
        return "—"
    return datetime.fromtimestamp(us / 1_000_000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def main() -> None:
    with STX(region="ontario", env="staging") as client:
        client.login(params={})

        # 1. Balances + tier — one query, narrow selection.
        acct = client.account(
            selections=Selection(
                "account_balance",
                "available_balance",
                "loyalty_tier",
                "total_deposits",
                "total_withdrawals",
                "points",
            )
        )
        print("Balances")
        print(f"  total:        {_fmt_cents(acct.account_balance)}")
        print(f"  available:    {_fmt_cents(acct.available_balance)}")
        print(f"  deposits:     {_fmt_cents(acct.total_deposits)}")
        print(f"  withdrawals:  {_fmt_cents(acct.total_withdrawals)}")
        print(f"  tier:         {acct.loyalty_tier or '—'}")
        print(f"  points:       {acct.points or 0:>10,.2f}")

        # 2. Loyalty history — recent point-bearing transactions. Items
        # are TransactionHistory; loyalty rows have a non-null `points`.
        loyalty = client.loyalty_history(
            params={"pagination": {"page": 0, "limit": 5}},
            selections=Selection("inserted_at", "type", "amount", "points"),
        )
        print(f"\nLoyalty activity (last {len(loyalty)})")
        if not loyalty:
            print("  (none)")
        for h in loyalty:
            print(
                f"  {_fmt_us(h.inserted_at):<17} "
                f"{(h.type or '—'):<14} "
                f"amount={_fmt_cents(h.amount)}  "
                f"points={h.points or 0:>+8.2f}"
            )

        # 3. Per-market stats — your position / fees / settled-contracts
        # across every market you've traded. Empty if you've never traded.
        stats = client.account_market_stats(
            params={"pagination": {"page": 0, "limit": 10}},
            selections=Selection(
                "market_id", "title", "contracts_settled",
                "total_fees", "total_settlement_pnl", "updated_at",
            ),
        )
        print(f"\nPer-market stats (top {len(stats)})")
        if not stats:
            print("  (no settled positions yet)")
        for s in stats:
            title = (s.title or "—")[:30]
            print(
                f"  {(s.market_id or '—'):<14} {title:<30} "
                f"contracts={s.contracts_settled or 0:>5}  "
                f"fees={_fmt_cents(s.total_fees)}  "
                f"pnl={_fmt_cents(s.total_settlement_pnl)}  "
                f"updated={_fmt_us(s.updated_at)}"
            )


if __name__ == "__main__":
    main()
