"""A small long-running worker: order books plus your own orders and fills.

The shape most bots start from. One process, one socket, three channels:

- ``orderbook`` for a handful of open markets: each ``book`` push is the
  full book for one market, so the worker replaces what it holds.
- ``orders`` for your order updates (``all_orders`` on join, then
  ``new_open_order``).
- ``fills`` for your executions (``all_trades`` on join, then ``trade``).

Every frame is printed with a timestamp and a running count. The worker
runs until Ctrl-C, or for ``--seconds N``. Heartbeat, channel pings,
reconnect and rejoin are handled by the SDK; ``on_reconnect`` is where
a real bot would take a fresh REST snapshot.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python worker.py                # until Ctrl-C
    python worker.py --seconds 60   # bounded run

Run ``safe_order_round_trip.py`` in a second shell to see order frames.
"""

import argparse
import asyncio
import signal
import sys
from collections import Counter
from typing import Dict, Optional

from demo_config import describe_target, hms, make_async_client, open_market_ids

DEPTH = 3


def _top(levels) -> str:
    if not levels:
        return "(empty)"
    return ", ".join(f"{lvl['quantity']}@{lvl['price']}" for lvl in levels[:DEPTH])


async def run(seconds: Optional[float]) -> None:
    counts: Counter = Counter()
    books: Dict[str, dict] = {}
    stop = asyncio.Event()

    def on_book(msg) -> None:
        p = msg.payload
        books[p["market_id"]] = p  # a full snapshot: replace, never merge
        counts["book"] += 1
        print(
            f"  [{hms()}] book   #{counts['book']:<5} {p['market_id']}  bids {_top(p['bids'])}  "
            f"offers {_top(p['offers'])}"
        )

    def on_order(msg) -> None:
        if msg.event == "all_orders":
            print(f"  [{hms()}] orders snapshot: {len(msg.payload['orders'])} open")
            return
        p = msg.payload
        counts["order"] += 1
        print(
            f"  [{hms()}] order  #{counts['order']:<5} {p['id']} {p['status']} filled "
            f"{p['filled']}/{p['quantity']} @ {p['price']}"
        )

    def on_fill(msg) -> None:
        if msg.event == "all_trades":
            print(f"  [{hms()}] fills  snapshot: {len(msg.payload['trades'])} open trades")
            return
        p = msg.payload
        counts["fill"] += 1
        print(
            f"  [{hms()}] fill   #{counts['fill']:<5} {p['id']} {p['action']} {p['filled']} @ "
            f"{p['price']} fee {p['total_fee']}"
        )

    async def on_reconnect() -> None:
        print(f"  [{hms()}] reconnected; a real bot would re-read open orders over REST here")

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows
            pass

    async with make_async_client() as client:
        me = await client.me()
        print(f"Authenticated as {me.user_id} ({me.scope}) on {describe_target()}")
        ids = await open_market_ids(client, 5)
        async with client.websocket(on_reconnect=on_reconnect) as ws:
            await ws.orderbook(ids, on_message=on_book)
            await ws.orders(on_message=on_order)
            await ws.fills(on_message=on_fill)
            print(
                f"Watching {len(ids)} books. "
                + ("Running until Ctrl-C..." if seconds is None else f"Running for {seconds:g}s...")
            )
            try:
                await asyncio.wait_for(stop.wait(), seconds)
            except asyncio.TimeoutError:
                pass

    print(
        f"\nStopped. {counts['book']} book, {counts['order']} order, {counts['fill']} fill "
        f"frame(s); {len(books)} books held."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seconds", type=float, default=None, help="stop after this many seconds")
    args = parser.parse_args()
    try:
        asyncio.run(run(args.seconds))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
