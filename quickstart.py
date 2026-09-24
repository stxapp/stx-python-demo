"""STX SDK Hello World: log in and pull a few open markets in 5 lines.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python quickstart.py

The smallest possible working example. For the production-grade login
flow (2FA, refresh, error branches) see ``auth_flow.py``. For all the
ways to shape the response, see ``list_markets.py``.

Requires stx-python 0.4.0a1 or newer (see requirements.txt).
"""
from stx import Selection

from demo_config import make_client


def main() -> None:
    with make_client() as client:
        client.login()

        page = client.markets(
            status=["OPEN"],
            limit=5,
            selections=Selection("market_id", "title", "status"),
        )
        print(f"Got {len(page)} of {page.count} open markets:")
        for m in page:
            print(f"  {m.market_id}: [{m.status}] {m.title}")


if __name__ == "__main__":
    main()
