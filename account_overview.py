"""Account overview: identity, cash movements, loyalty, per-market positions.

Read-only snapshot of what an API key can see about your STX account.
Useful as a first authenticated call (proves the key works) and as a
starting point for portfolio-tracking scripts.

An API key authenticates a trading integration rather than a person's
account settings, so the ``account`` and ``user_profile`` operations
are reserved for the session login path and rejected for a key. What a
key can read: ``me``, ``my_deposit_and_withdrawal_history``,
``loyalty_history``, ``account_market_stats``, plus every market,
order, trade and settlement query.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python account_overview.py

Note: monetary fields on the wire are integer cents; divide by 100
to display dollars.
"""
from __future__ import annotations  # PEP 604 union syntax in helpers (3.9 compat)

from datetime import datetime, timezone

from stx import Selection
from stx.exceptions import STXException

from demo_config import make_client


def _fmt_cents(c: int | None) -> str:
    if c is None:
        return "  -"
    return f"${c / 100:>10,.2f}"


def _fmt_us(us: int | None) -> str:
    """Render a UNIX-microseconds timestamp as a short ISO date."""
    if not us:
        return "-"
    return datetime.fromtimestamp(us / 1_000_000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def main() -> None:
    with make_client() as client:
        # 1. Who the key belongs to.
        me = client.me()
        print("Identity")
        print(f"  user_id:      {me.user_id}")
        print(f"  account_id:   {me.account_id}")
        print(f"  scope:        {me.scope.value if me.scope else '-'}")

        # 2. Deposits and withdrawals, most recent first. Items are
        # TransactionHistory rows with a `type` of deposit / withdrawal.
        print("\nDeposits and withdrawals (last 5)")
        try:
            moves = client.my_deposit_and_withdrawal_history(
                selections=Selection("inserted_at", "type", "amount", "method"),
            )
            if not moves:
                print("  (none)")
            for t in list(moves)[:5]:
                print(
                    f"  {_fmt_us(t.inserted_at):<17} "
                    f"{(t.type or '-'):<12} "
                    f"amount={_fmt_cents(t.amount)}  "
                    f"{t.method or '-'}"
                )
        except STXException as exc:
            print(f"  (server error, skipping: {type(exc).__name__})")

        # 3. Loyalty history, recent point-bearing transactions. Wrapped
        # because this operation can intermittently return a server
        # error, and a backend hiccup should not mask the rest of the demo.
        print("\nLoyalty activity (last 5)")
        try:
            loyalty = client.loyalty_history(
                pagination={"page": 0, "limit": 5},
                selections=Selection("inserted_at", "type", "amount", "points"),
            )
            if not loyalty:
                print("  (none)")
            for h in loyalty:
                print(
                    f"  {_fmt_us(h.inserted_at):<17} "
                    f"{(h.type or '-'):<14} "
                    f"amount={_fmt_cents(h.amount)}  "
                    f"points={h.points or 0:>+8.2f}"
                )
        except STXException as exc:
            print(f"  (server error, skipping: {type(exc).__name__})")

        # 4. Per-market stats: your position, fees and settled contracts
        # across every market you have traded. Empty if you never traded.
        print("\nPer-market stats (top 10)")
        try:
            stats = client.account_market_stats(
                pagination={"page": 0, "limit": 10},
                selections=Selection(
                    "market_id", "title", "contracts_settled",
                    "total_fees", "total_settlement_pnl", "updated_at",
                ),
            )
            if not stats:
                print("  (no settled positions yet)")
            for s in stats:
                title = (s.title or "-")[:30]
                print(
                    f"  {(s.market_id or '-'):<14} {title:<30} "
                    f"contracts={s.contracts_settled or 0:>5}  "
                    f"fees={_fmt_cents(s.total_fees)}  "
                    f"pnl={_fmt_cents(s.total_settlement_pnl)}  "
                    f"updated={_fmt_us(s.updated_at)}"
                )
        except STXException as exc:
            print(f"  (server error, skipping: {type(exc).__name__})")


if __name__ == "__main__":
    main()
