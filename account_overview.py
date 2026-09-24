"""Account overview: identity, balance, positions, cash movements, per-market stats.

A read-only snapshot of what an API key can see about your account.
Every amount is printed as the API sends it: a dollar string such as
"154.7500". Nothing is converted.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python account_overview.py
"""

from stx import STXNotFoundException

from demo_config import make_client


def main() -> None:
    with make_client() as client:
        me = client.me()
        print("Identity")
        print(f"  user_id:      {me.user_id}")
        print(f"  account_id:   {me.account_id}")
        print(f"  scope:        {me.scope}")

        print("\nBalance")
        try:
            b = client.balance()
            print(f"  available:    {b.available_balance}")
            print(f"  cash:         {b.account_balance}")
            print(f"  liabilities:  buy {b.buy_order_liability}  sell {b.sell_order_liability}")
            print(f"  fee schedule: {b.fee_schedule}  tier {b.loyalty_tier}")
        except STXNotFoundException:
            print(
                "  (GET /api/v1/account/balance is not served here yet; the balances channel has "
                "it)"
            )

        print("\nOpen positions")
        try:
            positions = [p for p in client.positions() if p.position not in (None, "0.00")]
            if not positions:
                print("  (none)")
            for p in positions[:10]:
                print(
                    f"  {p.market_id}  net {p.position:>8}  premium {p.premium:>10}  open risk "
                    f"{p.open_risk}"
                )
        except STXNotFoundException:
            print(
                "  (GET /api/v1/positions is not served here yet; the positions channel has them)"
            )

        print("\nDeposits and withdrawals (last 5 each)")
        for name in ("deposits", "withdrawals"):
            rows = getattr(client, name)(limit=5)
            if not rows.items:
                print(f"  {name}: (none)")
            for t in rows:
                print(f"  {t.time}  {t.type:<11} {t.amount:>12}  {t.method or '-'}")

        print("\nLoyalty activity (last 5)")
        loyalty = client.loyalty(limit=5)
        if not loyalty.items:
            print("  (none)")
        for t in loyalty:
            print(f"  {t.time}  {t.type:<24} amount={t.amount}  points={t.points}")

        print("\nPer-market stats (top 10)")
        stats = client.account_market_stats(limit=10)
        if not stats.items:
            print("  (no markets traded yet)")
        for s in stats:
            print(
                f"  {(s.title or s.market_id)[:36]:<36} position={s.position:>8}  "
                f"fees={s.total_fees:>9}  net pnl={s.total_net_pnl:>10}"
            )


if __name__ == "__main__":
    main()
