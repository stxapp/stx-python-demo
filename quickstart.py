"""STX SDK Hello World: confirm who you are and pull a few open markets.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python quickstart.py

There is no login call: every request is signed with your API key.
``me()`` tells you which account the key belongs to. Prices and
quantities are strings exactly as the API sends them ("0.5600", "2.00").

Requires stx-python 0.6.0 or newer (see requirements.txt).
"""

from demo_config import make_client


def main() -> None:
    with make_client() as client:
        me = client.me()
        print(f"Authenticated as {me.user_id} (scope {me.scope})")

        page = client.markets(status="open", limit=5)
        print(f"{len(page)} open markets (more pages: {page.has_more}):")
        for m in page:
            print(f"  {m.market_id}  last={m.last_traded_price or '-':>7}  {m.title}")


if __name__ == "__main__":
    main()
