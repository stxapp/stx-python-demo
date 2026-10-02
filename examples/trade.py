"""Place one small buy order that will rest on the book, read it back, then cancel it.

The price is 1% of what a winning contract pays (one cent on a $1 contract),
and the script only uses a market where nobody is offering at that price or
lower, so the order rests instead of trading. It needs a read_write API key.

Run: python examples/trade.py
     SPORT=Football python examples/trade.py   (only look at markets in that sport)
"""

import os
import sys
import uuid

from stx import STX, STXRejectedException, STXValidationException

from helpers import find_resting_buy

with STX() as client:
    # 1. Find a market that accepts orders, whose event has not started, and a price that will rest.
    found = find_resting_buy(client, sport=os.environ.get("SPORT"))
    if found is None:
        print("No open market right now where a small buy would rest. Try again later.")
        sys.exit(0)
    market, price = found
    print(f"Market:  {market.event_title}: {market.title}")
    print(f"         {market.symbol}  (a winning contract pays {market.max_price})")

    # 2. Place the order. client_order_id is your own id: use it to find the order
    #    again if the call fails without an answer, instead of placing it twice.
    client_order_id = f"demo-{uuid.uuid4()}"
    order_id = None
    refused = False
    exit_code = 0
    try:
        order = client.place_order(
            market.market_id,
            "buy",
            "limit",
            price=price,  # a dollar string with whole cents, e.g. "0.01"
            quantity="1",  # one contract
            client_order_id=client_order_id,
        )
        order_id = order.id
        print(f"Placed:  buy 1 @ {price}  id {order_id}  status {order.status}")

        # 3. Read it back. The order is on the book and has not filled.
        current = client.order(order_id)
        print(
            f"Read:    status {current.status}  filled {current.filled} of {current.quantity}"
            f"  client id {current.client_order_id}"
        )
    except (STXRejectedException, STXValidationException) as exc:
        # The exchange explains why it refused the order, e.g. a read_only key or a market that just paused.
        refused = order_id is None
        print(f"Order refused ({exc.status_code}): {exc}", file=sys.stderr)
        exit_code = 1
    finally:
        # 4. Cancel it, whatever happened above. If placing failed without an answer
        #    the order may still exist, so look it up by client_order_id first.
        if order_id is None and not refused:
            matches = client.orders(client_order_ids=[client_order_id])
            order_id = matches[0].id if matches else None
        if order_id is not None:
            cancellation = client.cancel_order(order_id)
            print(f"Cancel:  {cancellation.order_id}  {cancellation.status}")

    # 5. Confirm the final state.
    if order_id is not None:
        done = client.order(order_id)
        print(f"Final:   status {done.status}  filled {done.filled}")
        if done.status != "cancelled":
            exit_code = 1

sys.exit(exit_code)
