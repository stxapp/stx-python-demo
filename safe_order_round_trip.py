"""Place a resting 1-cent limit buy, verify it, cancel it: the safest trading round trip.

What this shows:

- ``me()`` reports the key's scope; only a ``read_write`` key may trade.
- ``place_order`` takes price and quantity as strings, the way
  ``POST /api/v1/orders`` does: ``price="0.01", quantity="1"``.
- The order is visible through ``orders(client_order_ids=[...])`` and
  ``order(id)``.
- ``cancel_order`` removes it, and a ``finally`` block cancels anything
  left on the account even if the script fails part way.

Why it is safe: a buy at $0.01 does not cross the spread on a real
market, so it rests until cancelled; the quantity is one contract; and
the default target is the demo exchange, which uses no real money.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python safe_order_round_trip.py
"""

import sys
import uuid

from stx import STXAPIException

from demo_config import find_tradeable_market, make_client

PRICE = "0.01"
QUANTITY = "1"


def main() -> None:
    with make_client() as client:
        me = client.me()
        if me.scope != "read_write":
            print(
                f"This key has scope {me.scope}; placing orders needs read_write.", file=sys.stderr
            )
            raise SystemExit(0)

        market = find_tradeable_market(client)
        if market is None:
            print("No open, trading market with an unstarted event right now.", file=sys.stderr)
            raise SystemExit(0)
        print(f"Market: {market.symbol} (max price {market.max_price})")

        client_order_id = f"demo-{uuid.uuid4()}"
        try:
            print(f"Placing limit buy {QUANTITY} @ {PRICE}...")
            try:
                order = client.place_order(
                    market.market_id,
                    "buy",
                    "limit",
                    price=PRICE,
                    quantity=QUANTITY,
                    client_order_id=client_order_id,
                )
            except STXAPIException as exc:
                # 403: read-only key or account state; 422: the exchange
                # refused (closed market, funds). The message says which.
                print(f"The exchange refused the order ({exc.status_code}): {exc}")
                raise SystemExit(0) from None
            print(
                f"  placed: id={order.id} status={order.status} price={order.price} "
                f"qty={order.quantity}"
            )

            found = client.orders(client_order_ids=[client_order_id])
            print(f"  visible in orders(): {[o.status for o in found]}")
            print(f"  order(id): {client.order(order.id).status}")

            cancelled = client.cancel_order(order.id)
            print(f"  cancelled: {cancelled.order_id} -> {cancelled.status}")
            print(
                f"  now: {client.order(order.id).status} "
                f"({client.order(order.id).cancellation_reason})"
            )
        finally:
            leftovers = client.cancel_all_orders()
            if leftovers:
                print(f"  cleanup cancelled {len(leftovers)} leftover order(s)")


if __name__ == "__main__":
    main()
