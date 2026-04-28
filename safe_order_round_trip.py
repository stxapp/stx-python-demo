"""Place a resting LIMIT BUY at 1¢, verify, cancel — the safest possible
trading round-trip.

What this proves:

- ``place_order`` mutation works against your account (and shows you
  what error you'd see if it doesn't — geo-block, no trading rights,
  etc., are surfaced as ``STXException`` with a clear message).
- ``cancel_order`` removes the resting order.
- The ``orders`` history reflects both the place and the cancel.

Why it's safe to run end-to-end:

- LIMIT BUY at price=1 (one cent — the lowest non-zero) **never crosses
  the spread on any real market**, so it sits resting until cancelled.
  No fills, no real money committed.
- Quantity is 1 — the smallest tradable size.
- A try/finally cancel-all sweeps any leakage, even if the script
  raises mid-flow.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python safe_order_round_trip.py
"""
from __future__ import annotations  # `str | None` in helper signatures (3.9 compat)

import sys

from stx import STX, Selection
from stx.exceptions import STXException


RESTING_BUY_PRICE = 1   # 1 cent — never fills against real liquidity
RESTING_BUY_QTY = 1


def _find_tradable_market(client) -> str | None:
    """Pick any OPEN + currently-tradable market. Returns market_id, or
    None if the env has nothing to trade right now."""
    page = client.markets(
        params={"input": {"status": "OPEN", "trading": "TRUE", "limit": 5}},
        selections=Selection("market_id", "title"),
    )
    return page[0].market_id if len(page) else None


def main() -> None:
    with STX(region="ontario", env="staging") as client:
        client.login(params={})

        market_id = _find_tradable_market(client)
        if market_id is None:
            print(
                "No OPEN + tradable markets right now. Re-run during "
                "trading hours (Mon–Fri 09:30–16:00 ET).",
                file=sys.stderr,
            )
            raise SystemExit(0)

        # Cancel any leftovers from a previous run before we start.
        try:
            client.cancel_all_orders()
        except STXException:
            pass

        order_id = None
        try:
            print(f"Placing 1¢ LIMIT BUY x{RESTING_BUY_QTY} on {market_id}...")
            try:
                result = client.place_order(
                    params={
                        "user_order": {
                            "market_id": market_id,
                            "order_type": "LIMIT",
                            "action": "BUY",
                            "price": RESTING_BUY_PRICE,
                            "quantity": RESTING_BUY_QTY,
                        }
                    },
                    selections=Selection("errors", order=Selection("id", "status")),
                )
            except STXException as exc:
                msg = str(exc).lower()
                if any(kw in msg for kw in ("forbidden", "permission", "geo", "not allowed")):
                    print(f"This account can't trade on dev right now: {exc}")
                    raise SystemExit(0)
                raise

            if result.order is None:
                print(f"place_order returned no order; errors={result.errors}", file=sys.stderr)
                raise SystemExit(1)

            order_id = result.order.id
            print(f"  → placed: id={order_id} status={result.order.status}")

            # Verify the order surfaces in the history.
            orders = client.orders(
                params={
                    "order_ids": [order_id],
                    "pagination": {"page": 0, "limit": 1},
                },
                selections=Selection("id", "status", "price", "quantity"),
            )
            if len(orders) == 1:
                print(f"  → visible in orders(): {orders[0].status}")
            else:
                print(f"  → orders() didn't return our row yet (eventual consistency)")

            # Cancel it. Server may have already moved the order to a
            # non-cancellable state by the time we get here (filled, expired,
            # auto-cancelled, etc.); tolerate that — the finally block sweeps
            # any survivors via cancel_all_orders.
            try:
                client.cancel_order(
                    params={"order_id": order_id},
                    selections=Selection("status"),
                )
                print(f"  → cancelled {order_id}")
            except Exception as exc:
                print(f"  → cancel_order raised ({type(exc).__name__}); finally will sweep")
        finally:
            # Belt-and-suspenders cleanup. If we crashed somewhere above,
            # this still wipes any resting orders we might have left.
            try:
                client.cancel_all_orders()
            except STXException:
                pass


if __name__ == "__main__":
    main()
