"""Buy a small combo as a player, then cash it out, over one WebSocket.

A combo is one market over two or more legs: it pays only if every leg wins.
You ask makers to quote on the legs and a stake, they quote what you would
win, and accepting the best quote places an order for you on the combo's own
market. Cashing out works the same way in reverse, so the run ends holding
nothing. It needs a read_write API key.

Run: python examples/combos.py                  (a 2.00 stake on two legs; waits 20 s for each quote)
     python examples/combos.py 60               (waits up to 60 s for each quote)
     STAKE=5 LEGS=3 python examples/combos.py   (a 5.00 stake on three legs)
     SPORT=Football python examples/combos.py   (legs from one sport)
"""

import asyncio
import os
import sys
from decimal import Decimal

from stx import AsyncSTX, STXComboException, STXCombosUnavailableException
from stx.combos import BestQuote

from helpers import QuoteOutcome, cash_out_when_held, combo_stake, pick_combo_legs, take_best_quote

wait_seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 20
stake = combo_stake(os.environ.get("STAKE", "2"))
leg_count = int(os.environ.get("LEGS", "2"))


def quote_ref(q: BestQuote) -> str:
    return f"  (quote {q.quote_id})" if q.quote_id else ""


def not_placed(outcome: QuoteOutcome, what: str) -> str:
    if outcome.reason:
        return f"The request ended without a trade: {outcome.reason}."
    return (
        f"No {what} arrived within {wait_seconds:g} s. Makers quote combos as they choose;"
        " try again, or wait longer with python examples/combos.py 60."
    )


async def cancel_quietly(rfq, rfq_id: str) -> None:
    """End a request that may already have ended on its own."""
    try:
        await rfq.cancel(rfq_id)
    except STXComboException:
        pass


async def settled_position(client: AsyncSTX, market_id: str) -> str:
    """Your position in a market, read until it is flat or 10 seconds pass."""
    position = "0.00"
    for _ in range(10):
        held = await client.positions(market_ids=[market_id])
        position = (held[0].position if held else None) or "0.00"
        if Decimal(position) == 0:
            break
        await asyncio.sleep(1)
    return position


async def main() -> int:
    async with AsyncSTX() as client:
        # One signed socket carries the negotiation. Closing it ends any request still open.
        async with client.websocket() as ws:
            # 1. Join your player channel. An exchange without combos refuses the join.
            try:
                rfq = await ws.rfq()
            except STXCombosUnavailableException:
                print(f"Combos are not available on {client.base_url}.")
                return 1

            # 2. Pick the legs: open markets from different events that have not started.
            markets = await pick_combo_legs(client, count=leg_count, sport=os.environ.get("SPORT"))
            if len(markets) < leg_count:
                print(f"Found {len(markets)} open market(s) from different events; {leg_count} legs need {leg_count}.")
                return 0
            for i, m in enumerate(markets, start=1):
                print(f"Leg {i}:   {m.question or m.title}  ({m.short_title})")

            # 3. Ask for quotes. Every outcome is "won": the combo pays if all the legs win.
            legs = [(m.market_id, "won") for m in markets]
            try:
                request = await rfq.request_quote(legs, amount=stake)
            except STXComboException as exc:
                print(f"Request refused: {exc.reason}")  # e.g. insufficient_assets, leg_not_quotable
                return 1
            print(f"\nRequest: {request.rfq_id}  stake {stake}")
            print(f"Waiting up to {wait_seconds:g} s for a quote...")

            # 4. Take the best quote at its exact amount: what you win on your stake.
            def on_buy_quote(q: BestQuote) -> None:
                what = f"win {q.amount} on a {stake} stake" if q.amount else "none live"
                print(f"[quote]  {what}{quote_ref(q)}")

            bought = await take_best_quote(rfq, request.rfq_id, wait_seconds, on_buy_quote)
            if bought.placement is None:
                print(not_placed(bought, "quote"))
                await cancel_quietly(rfq, request.rfq_id)
                return 1
            placed = bought.placement
            combo = await client.market(placed.market_id)
            print(
                f"Bought:  {placed.quantity} @ {placed.price}  order {placed.order_id}  (accepted win {bought.amount})"
            )
            print(f"         combo {placed.market_id}  {combo.short_title}", end="  ")
            print(f"(a winning contract pays {combo.max_price})")

            # 5. Cash out: a new request to sell everything you hold of the combo.
            out = await cash_out_when_held(rfq, placed.market_id)
            print(f"\nCash out: {out.rfq_id}  selling {out.quantity}")

            def on_sell_quote(q: BestQuote) -> None:
                what = f"pays {q.amount} for all {out.quantity}" if q.amount else "none live"
                print(f"[quote]  {what}{quote_ref(q)}")

            sold = await take_best_quote(rfq, out.rfq_id, wait_seconds, on_sell_quote)
            if sold.placement is None:
                print(not_placed(sold, "cash-out quote"))
                print(f"You still hold {out.quantity} of combo {placed.market_id}.", end=" ")
                print("Run again later, or sell it on its order book.")
                await cancel_quietly(rfq, out.rfq_id)
                return 1
            s = sold.placement
            print(f"Sold:    {s.quantity} @ {s.price}  order {s.order_id}  (accepted {sold.amount})")

        # 6. Confirm nothing is left: no position and no resting order on the combo.
        #    A trade shows in your position a moment after it fills, so look a few times.
        position = await settled_position(client, placed.market_id)
        resting = await client.orders(market_ids=[placed.market_id], status=["open", "delayed"])
        for order in resting:
            await client.cancel_order(order.id)  # the unfilled rest of an order the maker did not fully take
        orders_left = f"{len(resting)}, cancelled" if resting else "0"
        print(f"Final:   position {position} on the combo  open orders {orders_left}")
        return 0 if Decimal(position) == 0 else 1


sys.exit(asyncio.run(main()))
