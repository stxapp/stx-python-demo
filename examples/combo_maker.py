"""Quote every combo request as a maker, and report how each one ends.

Players ask for quotes on a combo: a set of legs and a stake to buy, or a
combo they hold to cash out. Every maker joined to its combo_quote channel
receives each request. This script quotes all of them and prints what
happens next: your quote placed (quote_accepted, then placed), another
maker's placed instead (placed_elsewhere), your quote expiring, and the
request closing. It needs a read_write API key.

On a buy you quote what the player wins: the stake times WIN_MULTIPLE. On a
cash out you quote what you pay for everything the player sells:
CASH_OUT_PRICE a contract. Each quote stands for QUOTE_SECONDS. With PLAYER
set to a player's external_id, it quotes only that player's requests.

Run: python examples/combo_maker.py              (quote until Ctrl-C)
     python examples/combo_maker.py 120          (stop after 120 s)
     WIN_MULTIPLE=12 CASH_OUT_PRICE=0.10 QUOTE_SECONDS=60 python examples/combo_maker.py
"""

import asyncio
import os
import sys
import time

from stx import AsyncSTX, STXComboException, STXCombosUnavailableException
from stx.combos import ComboQuoteChannel, RfqOpened

from helpers import maker_quote_amount

run_seconds = float(sys.argv[1]) if len(sys.argv) > 1 else None
win_multiple = os.environ.get("WIN_MULTIPLE", "9")
cash_out_price = os.environ.get("CASH_OUT_PRICE", "0.08")
quote_ms = int(float(os.environ.get("QUOTE_SECONDS", "30")) * 1000)
player = os.environ.get("PLAYER")  # a player's external_id: quote only their requests


def short(uuid: str) -> str:
    return uuid[:8]


def describe(request: RfqOpened) -> str:
    if request.side == "buy":
        legs = ", ".join(f"{leg.short_name or short(leg.market_id)} {leg.outcome}" for leg in request.legs)
        return f"buy, stake {request.amount}, {len(request.legs)} legs: {legs}"
    return f"cash out of {request.quantity} on combo {short(request.market_id)}"


async def quote(quotes: ComboQuoteChannel, request: RfqOpened) -> None:
    amount = maker_quote_amount(request, win_multiple, cash_out_price)
    if amount is None:
        print(f"[skip]     {short(request.rfq_id)}  no amount prices inside 0 to {request.max_price}")
        return
    try:
        q = await quotes.quote(request.rfq_id, amount, quote_ms, client_order_id=f"maker-{short(request.rfq_id)}")
    except STXComboException as exc:
        # e.g. cannot_quote_own_request, or not_found when the request ended first
        print(f"[refused]  {short(request.rfq_id)}  {exc.reason}")
        return
    what = f"win {q.amount}" if request.side == "buy" else f"pay {q.amount} for {request.quantity}"
    print(f"[quoted]   {short(request.rfq_id)}  {what}  for {quote_ms // 1000} s  quote {q.quote_id}")


async def main() -> int:
    async with AsyncSTX() as client:
        # The SDK signs the socket, sends heartbeats and reconnects. Quotes belong to the
        # connection that placed them: a drop withdraws them, so there is nothing to clean up.
        async with client.websocket(
            on_reconnect=lambda: print("[reconnected]  quotes from before the drop were withdrawn")
        ) as ws:
            try:
                quotes = await ws.combo_quote()
            except STXCombosUnavailableException:
                print(f"Combos are not available on {client.base_url}.")
                return 1
            print(f"Quoting combos on {client.base_url} as a maker.")
            print(f"Buys: win {win_multiple}x the stake. Cash outs: {cash_out_price} a contract.", end=" ")
            print(f"Each quote stands {quote_ms // 1000} s. Ctrl-C to stop.\n")

            deadline = time.monotonic() + run_seconds if run_seconds else None
            quoting = set()  # with PLAYER set, the requests this maker takes part in
            while deadline is None or time.monotonic() < deadline:
                try:
                    msg = await quotes.next(timeout=deadline - time.monotonic() if deadline else None)
                except asyncio.TimeoutError:
                    break
                d = msg.data
                rfq = short(d.rfq_id) if d is not None else "-"
                if player and msg.event in ("rfq_opened", "rfq_closed"):
                    if msg.event == "rfq_opened" and d.external_id == player:
                        quoting.add(d.rfq_id)
                    if d.rfq_id not in quoting:
                        continue  # another player's request
                if msg.event == "rfq_opened":
                    # Every request opened after the join, from every player, your own included.
                    print(f"[request]  {rfq}  {describe(d)}")
                    await quote(quotes, d)
                elif msg.event == "quote_accepted":
                    # The player took your quote; the exchange is placing both orders now.
                    print(f"[accepted] {rfq}  quote {d.quote_id}")
                elif msg.event == "placed":
                    print(f"[won]      {rfq}  order {d.order_id}  {d.quantity} @ {d.price}  combo {d.market_id}")
                elif msg.event == "negotiation_closed":
                    # One of your quotes stopped standing, once per quote, with the reason.
                    label = {"placed_elsewhere": "[lost]   ", "expired": "[expired]"}.get(d.reason, "[ended]  ")
                    print(f"{label}  {rfq}  quote {d.quote_id}  {d.reason}")
                elif msg.event == "rfq_closed":
                    print(f"[closed]   {rfq}  {d.reason}")
    return 0


try:
    sys.exit(asyncio.run(main()))
except KeyboardInterrupt:
    print("\nStopped. Quotes still standing were withdrawn with the connection.")
