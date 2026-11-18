"""Place a post-only buy order, which only ever rests on the book as a maker, then cancel it.

A post-only order never takes liquidity: if it would match an offer on arrival,
the exchange does not place it. Like examples/trade.py, the script buys at 1% of
what a winning contract pays on a market where nobody offers that low, so the
order rests. It needs a read_write API key.

Not every exchange offers post-only orders yet. The SDK asks the exchange before
sending one, and where it is not offered the script says so and sends nothing.

Run: python examples/post_only.py
     SPORT=Football python examples/post_only.py   (only look at markets in that sport)
"""

import os
import sys
import uuid

from stx import (
    STX,
    STXBlockedException,
    STXNotAvailableError,
    STXPostOnlyWouldMatchException,
    STXRateLimitException,
    STXRejectedException,
    STXValidationException,
)

from helpers import find_resting_buy, market_name

with STX() as client:
    # 1. Ask the exchange which order fill modes it offers. place_order() checks this
    #    itself; asking first just lets the script explain the answer.
    caps = client.capabilities()
    print(f"Exchange: {caps.host} {caps.api_version}  post-only: {caps.available('orders.post_only')}")

    # 2. Find a market that accepts orders, whose event has not started, and a price that will rest.
    found = find_resting_buy(client, sport=os.environ.get("SPORT"))
    if found is None:
        print("No open market right now where a small buy would rest. Try again later.")
        sys.exit(0)
    market, price = found
    print(f"Market:   {market_name(market)}")
    print(f"          {market.symbol}  (a winning contract pays {market.max_price})")

    client_order_id = f"demo-po-{uuid.uuid4()}"
    order_id = None
    exit_code = 0
    try:
        # 3. Place it post-only.
        order = client.place_order(
            market.market_id,
            "buy",
            "limit",
            price=price,
            quantity="1",
            client_order_id=client_order_id,
            fill_mode="post_only",
        )
        order_id = order.id
        print(
            f"Placed:   buy 1 @ {price}  post-only  id {order_id}  status {order.status}  fill mode {order.fill_mode}"
        )
    except STXNotAvailableError as exc:
        # This exchange does not offer post-only orders yet. Nothing was sent.
        print(f"Not here: {exc}")
    except STXPostOnlyWouldMatchException as exc:
        # It would have traded on arrival, so the exchange did not place it.
        # reason is "auto_matching", or "match_with_self" when the offer it would take is your own.
        print(f"Not placed: it would have matched ({exc.reason})")
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
    finally:
        # 4. Cancel it if it is on the book.
        if order_id is not None:
            cancellation = client.cancel_order(order_id)
            print(f"Cancel:   {cancellation.order_id}  {cancellation.status}")

sys.exit(exit_code)
