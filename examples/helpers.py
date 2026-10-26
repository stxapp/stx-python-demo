"""Small helpers shared by the examples. Nothing here talks to the network on its own."""

import asyncio
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Any, Callable, Optional

from stx import STX, AsyncSTX, STXComboException, STXComboPriceMovedException
from stx.combos import BestQuote, CashOut, ComboPlacement, RfqOpened
from stx.models import Market


def best_bid(market: Market) -> str:
    """The best (highest) bid price as a string, or "-" when nobody is bidding."""
    # bids and offers both run from the highest price to the lowest.
    return market.bids[0].price if market.bids else "-"


def best_offer(market: Market) -> str:
    """The best (lowest) offer price as a string, or "-" when nobody is offering."""
    return market.offers[-1].price if market.offers else "-"


def market_name(market: Market) -> str:
    """The event and the market's question, e.g. "Away at Home: Will Home win?".

    Markets on one event can share a title (both sides of a game do), so the question tells them apart.
    """
    return f"{market.event_title}: {market.question or market.title}"


def describe_market(market: Market) -> str:
    """A one-line description of a market: its name, best bid and best offer."""
    return f"{market_name(market)}  bid {best_bid(market)}  offer {best_offer(market)}"


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
    return Decimal(best_offer(market)) > Decimal(price)


def upcoming(market: Market, now: Optional[datetime] = None) -> bool:
    """True when the market's event is scheduled and starts after `now` (default: the current time).

    An open market can belong to an event whose start time has passed but that is
    still marked scheduled. Nobody quotes those, so the examples skip them.
    A market with no event status or start time counts as upcoming.
    """
    if market.event_status and market.event_status != "scheduled":
        return False
    if not market.event_start:
        return True
    start = datetime.fromisoformat(market.event_start.replace("Z", "+00:00"))
    return start > (now or datetime.now(timezone.utc))


def upcoming_markets(
    markets: Iterable[Market], count: int, scan: int = 200, now: Optional[datetime] = None
) -> list[Market]:
    """The first `count` upcoming markets out of the first `scan` in `markets`."""
    found: list[Market] = []
    for seen, market in enumerate(markets, start=1):
        if seen > scan or len(found) >= count:
            break
        if upcoming(market, now):
            found.append(market)
    return found


def find_resting_buy(
    client: STX, sport: Optional[str] = None, scan: int = 200, now: Optional[datetime] = None
) -> Optional[tuple[Market, str]]:
    """The first open market that is accepting orders, whose event is upcoming
    (see upcoming()), and where a buy at resting_buy_price() would rest.

    Returns the market and that price, or None when none of the first `scan`
    markets fit. Pass `sport` (e.g. "Football") to look only at that sport.
    """
    markets = client.iter_markets(status="open", trading=True, sports=[sport] if sport else None)
    for seen, market in enumerate(markets, start=1):
        if seen > scan:
            break
        if not market.market_id or not market.max_price:
            continue
        if not upcoming(market, now):
            continue
        price = resting_buy_price(market.max_price)
        if would_rest(market, price):
            return market, price
    return None


def combo_stake(value: str) -> str:
    """A combo stake as a dollar string with two decimals, e.g. "2" becomes "2.00".

    The exchange takes whole cents and nothing below one cent.
    """
    if not re.fullmatch(r"\d+(\.\d{1,2})?", value.strip()):
        raise ValueError(f'a stake is dollars in whole cents, e.g. "2" or "2.50", not {value!r}')
    stake = Decimal(value.strip())
    if stake < Decimal("0.01"):
        raise ValueError(f"a stake must be at least one cent, not {value!r}")
    return f"{stake:.2f}"


async def pick_combo_legs(
    client: AsyncSTX,
    count: int = 2,
    sport: Optional[str] = None,
    scan: int = 500,
    now: Optional[datetime] = None,
) -> list[Market]:
    """Up to `count` legs for a combo.

    Open markets accepting orders, whose event is scheduled to start after
    `now`, each from a different event (two markets of one game can
    contradict each other), and never a combo itself. Fewer than `count` come
    back when the first `scan` markets do not have enough.
    """
    now = now or datetime.now(timezone.utc)
    legs: list[Market] = []
    events: set[str] = set()
    seen = 0
    async for market in client.iter_markets(status="open", trading=True, sports=[sport] if sport else None):
        seen += 1
        if seen > scan or len(legs) >= count:
            break
        if not market.market_id or market.archived or market.event_type == "combo":
            continue
        if not upcoming(market, now):
            continue
        event = market.event_id or market.market_id
        if event in events:
            continue
        events.add(event)
        legs.append(market)
    return legs


@dataclass
class QuoteOutcome:
    """How a request ended for take_best_quote().

    `placement` and `amount` are set when a quote was accepted, `reason` when
    the request closed without a trade, and neither when no quote arrived.
    """

    placement: Optional[ComboPlacement] = None
    amount: Optional[str] = None
    reason: Optional[str] = None


async def take_best_quote(
    rfq: Any,
    rfq_id: str,
    timeout: float,
    on_quote: Optional[Callable[[BestQuote], None]] = None,
) -> QuoteOutcome:
    """Wait up to `timeout` seconds for a live quote on `rfq_id` and accept it at its exact amount.

    When the best moves before the accept lands, it takes the new best if one
    is live, or waits for the next. Any other refusal of the accept comes back
    as `reason`, the exchange's reason. `on_quote` sees every best quote as it
    arrives, including the empty one sent when quotes are withdrawn.
    """
    deadline = time.monotonic() + timeout
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            return QuoteOutcome()
        try:
            msg = await rfq.next(timeout=left)
        except asyncio.TimeoutError:
            return QuoteOutcome()
        data = msg.data
        if data is None or data.rfq_id != rfq_id:
            continue
        if msg.event == "negotiation_closed":
            return QuoteOutcome(reason=data.reason)
        if msg.event != "best_quote":
            continue
        if on_quote:
            on_quote(data)
        best = data
        while best.quote_id and best.amount and time.monotonic() < deadline:
            try:
                placement = await rfq.accept(rfq_id, best.quote_id, best.amount)
                return QuoteOutcome(placement=placement, amount=best.amount)
            except STXComboPriceMovedException as exc:
                # The request stays open: take the live best, or wait for the next quote.
                best = exc.best_quote
                if on_quote:
                    on_quote(best)
            except STXComboException as exc:
                # Any other refusal, e.g. player_refused:nothing_to_sell when the holding changed under a cash out.
                return QuoteOutcome(reason=f"{exc.reason} ({exc.detail})" if exc.detail else exc.reason)


async def cash_out_when_held(rfq: Any, market_id: str, attempts: int = 15, delay: float = 1.0) -> CashOut:
    """Open a cash out of everything you hold of the combo `market_id`.

    A fill counts toward your position a moment after it trades, so straight
    after buying the exchange can answer `nothing_to_sell`: this tries again,
    up to `attempts` times, `delay` seconds apart.
    """
    attempt = 1
    while True:
        try:
            return await rfq.cash_out(market_id)
        except STXComboException as exc:
            if exc.reason != "nothing_to_sell" or attempt >= attempts:
                raise
        attempt += 1
        await asyncio.sleep(delay)


def maker_quote_amount(request: RfqOpened, win_multiple: str, cash_out_price: str) -> Optional[str]:
    """The amount a maker quotes on `request`, in whole cents, or None when it would be refused.

    On a buy the amount is what the player wins: the stake times `win_multiple`.
    On a cash out it is what you pay for the whole size: `cash_out_price` a
    contract. The exchange derives a price from the amount, rounded to the
    request's `tick_size` in your favour, and refuses a quote whose price is
    not above 0 and below `max_price` (`price_out_of_range`), or, on a buy,
    whose stake buys no whole contract (`below_one_contract`). This checks the
    same rules first, so the example does not send a quote it knows will fail.
    """
    max_price, tick = Decimal(request.max_price), Decimal(request.tick_size)
    if request.side == "buy":
        stake = Decimal(request.amount)
        amount = (stake * Decimal(win_multiple)).quantize(Decimal("0.01"), rounding=ROUND_FLOOR)
        if amount <= 0:
            return None
        # max_price x stake / (stake + amount), rounded up to the tick.
        price = (max_price * stake / (stake + amount) / tick).to_integral_value(rounding=ROUND_CEILING) * tick
        if not 0 < price < max_price or (stake / price).to_integral_value(rounding=ROUND_FLOOR) < 1:
            return None
    else:
        quantity = Decimal(request.quantity)
        amount = (quantity * Decimal(cash_out_price)).quantize(Decimal("0.01"), rounding=ROUND_FLOOR)
        # amount / quantity, rounded down to the tick.
        price = (amount / quantity / tick).to_integral_value(rounding=ROUND_FLOOR) * tick
        if not 0 < price < max_price:
            return None
    return f"{amount:.2f}"
