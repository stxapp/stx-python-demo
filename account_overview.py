"""Account overview — balances, loyalty tier, per-market positions.

Read-only snapshot of everything the SDK exposes about your STX
account. Useful as a first authenticated call after login (proves
auth works) and as a starting point for portfolio-tracking scripts.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python account_overview.py
"""
from stx import STX, Selection


def main() -> None:
    with STX(region="ontario", env="staging") as client:
        client.login(params={})

        # 1. Balances + tier — one query, narrow selection.
        acct = client.account(
            selections=Selection(
                "account_balance",
                "available_balance",
                "loyalty_tier",
            )
        )
        print("Balances")
        print(f"  total:     ${acct.account_balance or 0:.2f}")
        print(f"  available: ${acct.available_balance or 0:.2f}")
        print(f"  tier:      {acct.loyalty_tier or '—'}")

        # 2. Loyalty history — recent point activity.
        loyalty = client.loyalty_history(
            params={"pagination": {"page": 0, "limit": 5}},
            selections=Selection("amount", "date", "description"),
        )
        print(f"\nLoyalty activity (last {len(loyalty)})")
        if not loyalty:
            print("  (none)")
        for h in loyalty:
            print(f"  {h.date or '—':<20} {h.amount or 0:>+8} pts  {h.description or '—'}")

        # 3. Per-market stats — your position / fees / settled-contracts
        # across every market you've traded. Empty if you've never traded.
        stats = client.account_market_stats(
            params={"pagination": {"page": 0, "limit": 10}},
            selections=Selection(
                "market_id", "contracts_settled", "total_fees", "updated_at"
            ),
        )
        print(f"\nPer-market stats (top {len(stats)})")
        if not stats:
            print("  (no settled positions yet)")
        for s in stats:
            print(
                f"  {s.market_id or '—':<20} "
                f"contracts={s.contracts_settled or 0:>4}  "
                f"fees=${s.total_fees or 0:>7.2f}  "
                f"updated={s.updated_at or '—'}"
            )


if __name__ == "__main__":
    main()
