"""Batch orders: place several orders in one request, then cancel them.

``place_orders`` sends one ``POST /api/v1/orders/batched``. Each order is
a dict with the same fields as ``place_order``. The result has one entry
per order, in order, carrying either the placed ``order`` or the
``errors`` that stopped it; one rejected order does not stop the others.

This places two resting 1-cent and 2-cent buys plus one deliberately
invalid order (a fractional quantity, which the exchange rejects), then
cancels the placed ones by id with ``cancel_orders`` and sweeps anything
left with ``cancel_all_orders``.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python batch_orders.py
"""

import sys

from stx import STXNotFoundException

from demo_config import find_tradeable_market, make_client


def main() -> None:
    with make_client() as client:
        if client.me().scope != "read_write":
            print("Placing orders needs a read_write key.", file=sys.stderr)
            raise SystemExit(0)
        market = find_tradeable_market(client)
        if market is None:
            print("No open, trading market with an unstarted event right now.", file=sys.stderr)
            raise SystemExit(0)
        print(f"Market: {market.symbol}")

        def order(price: str, quantity: str) -> dict:
            return {
                "market_id": market.market_id,
                "action": "buy",
                "order_type": "limit",
                "price": price,
                "quantity": quantity,
            }

        try:
            try:
                results = client.place_orders(
                    [order("0.01", "1"), order("0.02", "1"), order("0.01", "1.5")]
                )
            except STXNotFoundException:
                print("This exchange does not serve POST /api/v1/orders/batched yet.")
                raise SystemExit(0) from None

            placed = []
            for i, r in enumerate(results, 1):
                if r.ok:
                    placed.append(r.order.id)
                    print(f"  #{i} placed   {r.order.id} {r.order.quantity} @ {r.order.price}")
                else:
                    print(f"  #{i} rejected {r.errors}")

            if placed:
                for c in client.cancel_orders(placed):
                    print(f"  cancelled {c.order_id} -> {c.status}")
        finally:
            leftovers = client.cancel_all_orders()
            print(f"cancel_all_orders swept {len(leftovers)} more")


if __name__ == "__main__":
    main()
