"""Post-only and fill-or-kill orders: one that rests, one that would cross, and one fill-or-kill.

1. A post-only buy at 1% of what a winning contract pays, on a market where nobody
   offers that low: it rests on the book as a maker. The script cancels it.
2. A post-only buy at the best offer: it would take liquidity, so the exchange
   cancels it on arrival (cancellation_reason auto_matching). Nothing trades.
3. A fill-or-kill buy of 1 contract at the best offer: it fills in full, or is
   cancelled with nothing filled. If it fills you hold 1 contract.

An exchange without fill modes may place the order as a normal limit order, which
can trade like any other order. Always check fill_mode on the order that comes
back. When step 1 shows the mode was not taken, the script cancels that order and
skips steps 2 and 3, since there they would be normal orders that trade.

It needs a read_write API key.

Run: python examples/fill_modes.py
     SPORT=Football python examples/fill_modes.py   (only look at markets in that sport)
"""

import os
import sys
import time
import uuid
from decimal import Decimal

from stx import (
    STX,
    STXBlockedException,
    STXNotAvailableError,
    STXPostOnlyWouldMatchException,
    STXRateLimitException,
    STXRejectedException,
    STXValidationException,
)

from helpers import best_offer, find_resting_buy, market_name, upcoming


def find_offered_market(client, sport=None, scan=1000):
    """An upcoming market with a resting offer at no more than half what a winning contract pays."""
    markets = client.iter_markets(status="open", trading=True, sports=[sport] if sport else None)
    for seen, market in enumerate(markets, start=1):
        if seen > scan:
            break
        if market.market_id and market.max_price and market.offers and upcoming(market):
            if Decimal(best_offer(market)) <= Decimal(market.max_price) / 2:
                return market
    return None


def wait_until_done(client, order_id, tries=20):
    """The order once it is filled or cancelled (a fill-or-kill order is decided at once)."""
    order = client.order(order_id)
    while order.status not in ("filled", "cancelled") and tries > 0:
        time.sleep(0.5)
        tries -= 1
        order = client.order(order_id)
    return order


sport = os.environ.get("SPORT")
exit_code = 0

with STX() as client:
    print(f"Exchange: {client.host}")
    try:
        # 1. Post-only at a price that rests.
        found = find_resting_buy(client, sport=sport)
        if found is None:
            print("No open market right now where a small buy would rest. Try again later.")
            sys.exit(0)
        market, price = found
        print(f"Market:   {market_name(market)}")
        print(f"          {market.symbol}  (a winning contract pays {market.max_price})")
        try:
            order = client.place_order(
                market.market_id,
                "buy",
                "limit",
                price=price,
                quantity="1",
                client_order_id=f"demo-po-{uuid.uuid4()}",
                fill_mode="post_only",
            )
        except STXNotAvailableError as exc:
            # This exchange has post-only orders switched off and placed nothing.
            print(f"Not here: {exc}")
            sys.exit(0)
        modes_on = order.fill_mode == "post_only"
        if modes_on:
            print(f"Rests:    buy 1 @ {price}  id {order.id}  status {order.status}  fill mode {order.fill_mode}")
        else:
            print(f"Placed as a normal order: buy 1 @ {price}  id {order.id}  fill mode {order.fill_mode}")
        cancellation = client.cancel_order(order.id)
        print(f"Cancel:   {cancellation.order_id}  {cancellation.status}")
        if cancellation.status != "cancelled":
            exit_code = 1
        if not modes_on:
            print("This exchange does not take fill modes, so the crossing examples are skipped.")
            sys.exit(exit_code)

        # 2. Post-only at the best offer: it would match, so it is cancelled on arrival.
        offered = find_offered_market(client, sport=sport)
        if offered is None:
            print("No market with an offer right now; skipping the crossing examples.")
            sys.exit(exit_code)
        offer = best_offer(offered)
        print(f"Market:   {market_name(offered)}  best offer {offer}")
        try:
            order = client.place_order(
                offered.market_id,
                "buy",
                "limit",
                price=offer,
                quantity="1",
                client_order_id=f"demo-po-x-{uuid.uuid4()}",
                fill_mode="post_only",
            )
            # The offer went before the order arrived, so it rests instead.
            print(f"Rests:    the offer moved; cancelling {order.id}")
            client.cancel_order(order.id)
        except STXPostOnlyWouldMatchException as exc:
            # reason is "auto_matching" (the exchange cancelled it; exc.order is that order),
            # or "match_with_self" when the offer it would take is your own.
            cancelled = exc.order
            filled = (cancelled.filled if cancelled else None) or "0"
            print(f"Crossing: post-only buy @ {offer} not placed ({exc.reason})  filled {filled}")

        # 3. Fill-or-kill at the best offer: all or nothing.
        order = client.place_order(
            offered.market_id,
            "buy",
            "limit",
            price=offer,
            quantity="1",
            client_order_id=f"demo-fok-{uuid.uuid4()}",
            fill_mode="fill_or_kill",
        )
        order = wait_until_done(client, order.id)
        if order.status == "filled":
            print(f"Fill-or-kill: buy 1 @ {offer}  filled {order.filled} at avg {order.avg_price}")
        elif order.status == "cancelled":
            print(f"Fill-or-kill: buy 1 @ {offer}  cancelled ({order.cancellation_reason}), nothing filled")
        else:
            print(f"Fill-or-kill: unexpected status {order.status}", file=sys.stderr)
            exit_code = 1
    except STXBlockedException as exc:
        # Refused before it reached the exchange, e.g. from a location or network it does not serve.
        # Retrying will not help; quote the reference to STX support.
        print(f"Blocked ({exc.reason}): {exc}  reference {exc.reference}", file=sys.stderr)
        exit_code = 1
    except STXRateLimitException as exc:
        # Too many requests. The SDK already waited and retried; this is what was left.
        print(f"Rate limited: retry after {exc.retry_after} s  reference {exc.reference}", file=sys.stderr)
        exit_code = 1
    except (STXRejectedException, STXValidationException) as exc:
        print(f"Order refused ({exc.status_code}): {exc}", file=sys.stderr)
        exit_code = 1

sys.exit(exit_code)
