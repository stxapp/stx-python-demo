"""Stream a market's order book and your live account over one WebSocket, then exit.

It watches the same market that examples/trade.py uses, so running the trade
example in a second terminal shows the order arriving on both streams.

Run: python examples/live.py              (streams for 30 seconds)
     python examples/live.py 60           (streams for 60 seconds)
     SPORT=Football python examples/live.py   (watch a market in that sport, as trade does)
"""

import asyncio
import os
import sys
from decimal import Decimal

from stx import STX, AsyncSTX, ChannelMessage

from helpers import find_resting_buy

seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 30

# Pick the market with the blocking client, the same way trade.py does.
with STX() as client:
    found = find_resting_buy(client, sport=os.environ.get("SPORT"))
if found is None:
    print("No open market to watch right now.")
    sys.exit(0)
market, _ = found


def top(levels) -> str:
    """The best level of one side of a book as "quantity @ price", or "-"."""
    return f"{levels[0]['quantity']} @ {levels[0]['price']}" if levels else "-"


def on_book(msg: ChannelMessage) -> None:
    # Each "book" push is the market's whole book: replace what you hold, do not merge.
    if msg.event == "book":
        print(f"[book]    best bid {top(msg.payload['bids'])}  best offer {top(msg.payload['offers'])}")


def on_account(msg: ChannelMessage) -> None:
    # One line per account update. The payloads are documented per channel on docs.stxapp.io.
    if msg.is_snapshot:
        return  # the starting state is printed once, below
    p = msg.payload
    if msg.event == "new_open_order":
        print(f"[account] order {p['action']} {p['quantity']} @ {p['price']}  {p['status']}  filled {p['filled']}")
    elif msg.event == "trade":
        print(f"[account] fill {p['action']} {p['filled']} @ {p['price']}")
    elif msg.event == "update":
        print(f"[account] balance available {p['available_balance']}")
    elif msg.event == "updated_positions":
        print(f"[account] positions {len(p['positions'])} updated")
    else:
        print(f"[account] {msg.event}")


async def main() -> None:
    print(f"Watching {market.event_title}: {market.title}")
    bids = [level.model_dump() for level in market.bids or []]
    offers = [level.model_dump() for level in market.offers or []]
    print(f"[book]    best bid {top(bids)}  best offer {top(offers)}  (starting snapshot)")

    async with AsyncSTX() as client:
        # One signed socket carries every channel. The client sends heartbeats and reconnects for you.
        async with client.websocket() as ws:
            # The order book channel pushes the market's whole book each time it changes.
            await ws.orderbook([market.market_id], on_message=on_book)

            # The account channel carries your balance, orders, fills and positions on one join:
            # a snapshot of each first, then every change.
            account = await ws.account(on_message=on_account)
            snap = await account.wait_snapshot()
            open_orders = [o for o in snap["all_orders"]["orders"] if o["status"] in ("open", "delayed")]
            # Markets you have traded out of stay in the list with position 0; skip those.
            positions = [p for p in snap["all_positions"]["positions"] if Decimal(p["position"] or "0") != 0]
            print(
                f"[account] available {snap['balances']['available_balance']}"
                f"  open orders {len(open_orders)}  positions {len(positions)}"
            )

            print(
                f"\nStreaming for {seconds:g} s. Run examples/trade.py in another terminal to see an order come and go."
            )
            print()
            await asyncio.sleep(seconds)

        still_open = await client.orders(status=["open", "delayed"])
        print(f"\nClosed. Open orders now: {len(still_open)}")


asyncio.run(main())
