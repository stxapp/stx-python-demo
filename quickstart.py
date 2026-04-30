"""STX SDK Hello World — log in and pull a few open markets in 5 lines.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python quickstart.py

The smallest possible working example. For the production-grade login
flow (2FA, refresh, error branches) see ``auth_flow.py``. For all the
ways to shape the response, see ``list_markets.py``.

Compatible with stx-python >= 0.3.0a3.
"""
from stx import STX, Selection


def main() -> None:
    with STX(region="ontario", env="staging") as client:
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
