"""Identity: learn who the API key belongs to with ``me()``.

Under API-key authentication there is no login call and no session.
Each request is signed individually, so the first useful thing to do at
startup is ask the exchange who you are:

- ``user_id`` / ``account_id`` identify the account behind the key. The
  user id is what the per-user WebSocket channels (orders, trades,
  portfolio, settlements) are keyed on; calling ``me()`` once seeds it
  for every client in the process, so do this before joining any of
  those channels.
- ``scope`` is ``read_only`` or ``read_write``. Placing or cancelling
  orders needs ``read_write``; check it up front rather than discovering
  it from a rejected order.
- ``method`` reports how you authenticated (``api_key`` here).

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python identity.py
"""
import sys

from stx import Selection
from stx.exceptions import STXAuthException, STXConfigException
from stx.models import AccessScope

from demo_config import describe_target, make_client


def main() -> None:
    try:
        client = make_client()
    except STXConfigException as exc:
        # Key id without key material, a PEM that is not Ed25519, and
        # similar problems are caught at construction time, before any
        # request is made.
        print(f"Configuration problem: {exc}", file=sys.stderr)
        raise SystemExit(1)

    with client:
        try:
            me = client.me()
        except STXAuthException as exc:
            # The signature was rejected: wrong key id, a revoked key,
            # or a host clock more than 30 seconds off.
            print(f"Authentication failed: {exc}", file=sys.stderr)
            raise SystemExit(1)

        print(f"Connected to {describe_target()}")
        print(f"  user_id:     {me.user_id}")
        print(f"  account_id:  {me.account_id}")
        print(f"  name:        {(me.first_name or '')} {(me.last_name or '')}".rstrip())
        print(f"  method:      {me.method.value if me.method else '-'}")
        print(f"  scope:       {me.scope.value if me.scope else '-'}")
        print(f"  key_id:      {me.key_id or '-'}")

        can_trade = me.scope == AccessScope.READ_WRITE
        print(
            "\nThis key can place and cancel orders."
            if can_trade
            else "\nThis key is read-only: market data and history work, trading is rejected."
        )

        # One authenticated read to show the key in use. Nothing else to
        # do for auth: the SDK signs this request the same way it did me().
        page = client.markets(limit=3, selections=Selection("market_id", "title"))
        print(f"  markets reachable: {len(page)} of {page.count}")


if __name__ == "__main__":
    main()
