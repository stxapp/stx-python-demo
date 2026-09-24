"""STX SDK Hello World: confirm who you are and pull a few open markets.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python quickstart.py

The smallest possible working example. There is no login call: every
request is signed with your API key. ``me()`` is the one round trip
that tells you which account the key belongs to. For all the ways to
shape a response, see ``list_markets.py``.

Requires stx-python 0.6.0 or newer (see requirements.txt).
"""
from stx import Selection

from demo_config import make_client


def main() -> None:
    with make_client() as client:
        me = client.me()
        print(f"Authenticated as {me.user_id} (scope {me.scope.value})")

        page = client.markets(
            status="OPEN",
            limit=5,
            selections=Selection("market_id", "title", "status"),
        )
        print(f"Got {len(page)} of {page.count} open markets:")
        for m in page:
            print(f"  {m.market_id}: [{m.status}] {m.title}")


if __name__ == "__main__":
    main()
