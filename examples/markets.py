"""List upcoming markets that are open and accepting orders, with their best bid and offer.

Run: python examples/markets.py
"""

from stx import STX

from helpers import describe_market, upcoming_markets

# Reads your API key and exchange from STX_* environment variables or ~/.stx/credentials.
with STX() as client:
    # status "open": markets that have opened for trading (not scheduled, closed or settled).
    # trading=True: only markets accepting orders right now (an open market can be paused).
    # client.iter_markets() walks every page for you; client.markets() returns one page.
    markets = client.iter_markets(status="open", trading=True)

    # Markets come soonest event first, and an event whose start time has passed can still be open.
    # Keep the first 5 whose event has not started yet: those are the ones with live quotes.
    shown = upcoming_markets(markets, count=5)

    for market in shown:
        # bids are what buyers will pay, offers what sellers will accept.
        # describe_market() prints the best of each: the highest bid and the lowest offer.
        # Prices are dollars per contract, as strings; a winning contract pays market.max_price.
        print(describe_market(market))

    print(f"\n{len(shown)} upcoming markets shown.")
