"""STX auth flow: the three branches every production caller handles.

1. **Happy path**: email/password login, no 2FA enabled on the account.
2. **2FA branch**: server emailed/SMS'd a one-time code; submit it via
   ``confirm_2fa``. Required for accounts that have 2FA on.
3. **Token refresh**: STX access tokens expire after 60 minutes. The
   SDK handles this transparently: every authenticated call goes
   through an auth wrapper that checks expiry and, if needed, exchanges
   the cached refresh token for a fresh access token before the request
   hits the wire. **You don't write any refresh code.** Long-running
   bots get uninterrupted operation for free.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python auth_flow.py
"""
import sys

from stx import Selection
from stx.exceptions import STXAuthException, STXTwoFactorRequiredException
from stx.user import User

from demo_config import make_client


def main() -> None:
    client = make_client()

    # ---- 1. Login (happy path) + 2. 2FA branch -----------------------
    try:
        client.login()
    except STXTwoFactorRequiredException as exc:
        # Server sent a one-time code; collect from the user and confirm.
        # Falls through to a clear error if running non-interactively
        # (e.g., CI) so the failure mode is obvious.
        print(f"2FA required: {exc.message}")
        try:
            code = input("Enter 2FA code: ").strip()
        except EOFError:
            print(
                "stdin closed. Re-run with a 2FA-disabled account, or "
                "run this script interactively to enter the code.",
                file=sys.stderr,
            )
            raise SystemExit(1)
        client.confirm_2fa(code=code)
    except STXAuthException as exc:
        print(f"Login failed: {exc.message}", file=sys.stderr)
        raise SystemExit(1)

    user = User()
    print("Logged in.")
    print(f"  uid:                {user.uid}")
    print(f"  access expires:     {user.expiry}  (≈59 min from now)")
    print(f"  refresh_token set:  {bool(user.refresh_token)}")

    # ---- 3. Token refresh: happens automatically --------------------
    # No code required. Fire a couple of authenticated calls; the auth
    # wrapper transparently exchanges the refresh token for a fresh
    # access token whenever the cached one is past expiry. The user
    # of this SDK never writes refresh logic.
    acct = client.account(selections=Selection("available_balance", "loyalty_tier"))
    print(f"  balance:            ${acct.available_balance or 0:.2f}")
    print(f"  tier:               {acct.loyalty_tier or '-'}")

    page = client.markets(
        limit=3,
        selections=Selection("market_id", "title"),
    )
    print(f"  markets reachable:  {len(page)} of {page.count}")

    client.close()


if __name__ == "__main__":
    main()
