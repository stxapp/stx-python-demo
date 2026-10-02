"""List markets that are open and accepting orders, with their best bid and offer.

Run: python examples/markets.py
"""

from stx import STX

from helpers import describe_market

# Reads your API key and exchange from STX_* environment variables or ~/.stx/credentials.
with STX() as client:
    # status "open": markets that have opened for trading (not scheduled, closed or settled).
    # trading=True: only markets accepting orders right now (an open market can be paused).
    # limit: markets per page. Looping over page gives this page; client.iter_markets() walks every page.
    page = client.markets(status="open", trading=True, limit=5)

    for market in page:
        # bids are what buyers will pay, offers what sellers will accept, best price first.
        # Prices are dollars per contract, as strings; a winning contract pays market.max_price.
        print(describe_market(market))

    print(f"\n{len(page)} markets shown{', more available' if page.has_more else ''}.")
