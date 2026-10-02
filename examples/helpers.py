"""Small helpers shared by the examples. Nothing here talks to the network on its own."""

from decimal import ROUND_FLOOR, Decimal
from typing import Optional

from stx import STX
from stx.models import Market


def best_bid(market: Market) -> str:
    """The best bid price as a string, or "-" when nobody is bidding."""
    return market.bids[0].price if market.bids else "-"


def best_offer(market: Market) -> str:
    """The best offer price as a string, or "-" when nobody is offering."""
    return market.offers[0].price if market.offers else "-"


def describe_market(market: Market) -> str:
    """A one-line description of a market: event, market title, best bid and offer."""
    return f"{market.event_title}: {market.title}  bid {best_bid(market)}  offer {best_offer(market)}"


def resting_buy_price(max_price: str) -> str:
    """A buy price far below anything a seller is likely to accept.

    1% of what a winning contract pays, in whole cents, and never less than
    one cent. A market whose contract pays "1.0000" gives "0.01"; one that
    pays "100.0000" gives "1.00". Prices are read from the market, never
    assumed. Money stays in Decimal: never use floats for prices.
    """
    cents = Decimal(max_price) * 100
    if cents < 2:
        raise ValueError(f"cannot derive a resting price from max_price {max_price!r}")
    price_cents = max(Decimal(1), (cents / 100).to_integral_value(rounding=ROUND_FLOOR))
    return f"{price_cents / 100:.2f}"


def would_rest(market: Market, price: str) -> bool:
    """True when a buy at `price` would rest on the book instead of trading:
    nobody is offering, or the best offer is above `price`."""
    if not market.offers:
        return True
    return Decimal(market.offers[0].price) > Decimal(price)


def find_resting_buy(client: STX, sport: Optional[str] = None, scan: int = 200) -> Optional[tuple[Market, str]]:
    """The first open market that is accepting orders, whose event has not
    started, and where a buy at resting_buy_price() would rest.

    Returns the market and that price, or None when none of the first `scan`
    markets fit. Pass `sport` (e.g. "Football") to look only at that sport.
    """
    markets = client.iter_markets(status="open", trading=True, sports=[sport] if sport else None)
    for seen, market in enumerate(markets, start=1):
        if seen > scan:
            break
        if not market.market_id or not market.max_price:
            continue
        if market.event_status and market.event_status != "scheduled":
            continue
        price = resting_buy_price(market.max_price)
        if would_rest(market, price):
            return market, price
    return None
