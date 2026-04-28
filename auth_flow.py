"""STX auth flow — the three branches every production caller handles.

1. **Happy path** — email/password login, no 2FA enabled on the account.
2. **2FA branch** — server emailed/SMS'd a one-time code; submit it via
   ``confirm_2fa``. Required for accounts that have 2FA on.
3. **Token refresh** — STX tokens expire after 60 minutes. The SDK
   transparently calls ``new_token`` on the next authenticated request
   past the 59-minute mark, but you can also force a refresh yourself
   (useful right before a long-running operation).

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python auth_flow.py
"""
import sys

from stx import STX, Selection
from stx.exceptions import STXAuthException, STXTwoFactorRequiredException
from stx.user import User


def main() -> None:
    client = STX(region="ontario", env="staging")

    try:
        client.login(params={})
    except STXTwoFactorRequiredException as exc:
        # Server sent a one-time code; collect from the user and confirm.
        # Falls through to a clear error if running non-interactively
        # (e.g., CI) so the failure mode is obvious.
        print(f"2FA required: {exc.message}")
        try:
            code = input("Enter 2FA code: ").strip()
        except EOFError:
            print(
                "stdin closed — re-run with a 2FA-disabled account, or "
                "run this script interactively to enter the code.",
                file=sys.stderr,
            )
            raise SystemExit(1)
        client.confirm_2fa(params={"code": code})
    except STXAuthException as exc:
        print(f"Login failed: {exc.message}", file=sys.stderr)
        raise SystemExit(1)

    user = User()
    print("Logged in.")
    print(f"  uid:           {user.uid}")
    print(f"  token expires: {user.expiry}  (≈59 min from now)")

    # Force a token refresh. The SDK does this automatically when an
    # authenticated call lands past the 59-minute mark; calling it
    # yourself is rare but useful for long-running bots that want a
    # fresh token before a known-busy window.
    client.new_token(params={})
    print(f"  refreshed:     {user.expiry}")

    # Sanity — auth still works after the refresh.
    acct = client.account(selections=Selection("available_balance"))
    print(f"  balance:       {acct.available_balance}")

    client.close()


if __name__ == "__main__":
    main()
