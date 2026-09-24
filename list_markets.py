"""List the most active open markets: the view you open to find something to trade.

Pulls open, trading markets page by page, sorts by 24-hour volume and
prints a table. Prices and volumes are printed exactly as the API sends
them (dollar strings, contract counts as quantity strings); ``Decimal``
does the sorting so no float ever touches a money value.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python list_markets.py
"""

from decimal import Decimal
from itertools import islice

from demo_config import make_client

TOP_N = 20
SCAN = 400  # markets to look at; iter_markets follows the cursor for us


def _volume(market) -> Decimal:
    return Decimal(market.volume24h) if market.volume24h else Decimal(0)


def main() -> None:
    with make_client() as client:
        markets = list(islice(client.iter_markets(status="open", trading=True, limit=200), SCAN))
        active = sorted(markets, key=_volume, reverse=True)[:TOP_N]
        print(f"Top {len(active)} markets by 24h volume (of {len(markets)} scanned)\n")

        header = f"  {'SPORT':<12} {'TITLE':<44} {'BID':>7} {'OFFER':>7} {'LAST':>7} {'24h VOL':>9}"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for m in active:
            bid = m.bids[0].price if m.bids else "-"
            offer = m.offers[0].price if m.offers else "-"
            print(
                f"  {(m.sport or '-')[:12]:<12} {(m.title or '-')[:44]:<44} "
                f"{bid:>7} {offer:>7} {m.last_traded_price or '-':>7} {m.volume24h or '-':>9}"
            )


if __name__ == "__main__":
    main()
