"""A small long-running worker: market updates plus your own orders.

The shape most bots start from. One process, one socket, two
subscriptions:

- ``MARKETS`` (broadcast) narrowed server-side to bids and offers, so
  the frames stay small.
- ``ORDERS`` (per user) for state transitions on your own orders.

Each frame is printed with a timestamp and a running count. The worker
runs until Ctrl-C, or for ``--seconds N`` if you pass it (handy for CI
and for a first run). Reconnect, heartbeat and resubscribe are handled
by the SDK, so a dropped connection resumes on its own.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python worker.py                # until Ctrl-C
    python worker.py --seconds 60   # bounded run

To see an ORDERS frame, run ``safe_order_round_trip.py`` in a second
shell while this is listening.
"""
from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from collections import Counter
from datetime import datetime

from stx.enums import Channels

from demo_config import describe_target, make_client, make_ws

DEPTH = 3


def _hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _top(side, label: str) -> str:
    if not side:
        return f"{label}=(empty)"
    rows = []
    for lvl in (side or [])[:DEPTH]:
        if isinstance(lvl, dict):
            rows.append(f"{lvl.get('price')}x{lvl.get('quantity') or lvl.get('size')}")
    return f"{label}=[{', '.join(rows)}]"


async def run(seconds: float | None) -> None:
    # One me() call at startup: it proves the key works and seeds the
    # user id that the ORDERS topic is keyed on.
    with make_client() as client:
        me = client.me()
    print(f"Authenticated as {me.user_id} (scope {me.scope.value}) on {describe_target()}")

    counts: Counter = Counter()
    stop = asyncio.Event()

    async def on_market(msg) -> None:
        if msg.is_join_reply:
            print(f"  [{_hms()}] markets  joined  status={msg.reply_status}")
            return
        if msg.is_reply:
            return
        # Frames are dicts keyed by market_id, one entry per market.
        for market_id, m in (msg.payload or {}).items():
            if "bids" not in m and "offers" not in m:
                continue  # a status tick with no book change
            counts["market"] += 1
            print(
                f"  [{_hms()}] markets  #{counts['market']:<6} "
                f"{market_id}  {_top(m.get('bids'), 'bids')}  "
                f"{_top(m.get('offers'), 'offers')}"
            )

    async def on_order(msg) -> None:
        if msg.is_join_reply:
            print(f"  [{_hms()}] orders   joined  status={msg.reply_status}")
            return
        if msg.is_reply:
            return
        p = msg.payload or {}
        if msg.event == "all_orders":
            # Snapshot of your resting orders, sent once on join.
            print(f"  [{_hms()}] orders   snapshot  {len(p.get('orders') or [])} resting")
            return
        counts["order"] += 1
        print(
            f"  [{_hms()}] orders   #{counts['order']:<6} "
            f"{msg.event} id={p.get('id')} status={p.get('status')} "
            f"filled={p.get('filled')}/{p.get('quantity')}"
        )

    # Ctrl-C (SIGINT) and `timeout` / a supervisor (SIGTERM) both end the
    # run through the same path, so the socket is closed cleanly.
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows
            pass

    async with make_ws() as ws:
        await ws.join(
            Channels.MARKETS,
            on_message=on_market,
            join_params={"fields": ["bids", "offers"], "message_types": ["market_updated"]},
        )
        await ws.join(Channels.ORDERS, on_message=on_order)
        if seconds is None:
            print("Running until Ctrl-C...")
        else:
            print(f"Running for {seconds:g}s...")
        try:
            await asyncio.wait_for(stop.wait(), seconds)
        except asyncio.TimeoutError:
            pass

    print(f"\nStopped. {counts['market']} market frame(s), {counts['order']} order frame(s).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--seconds", type=float, default=None,
        help="stop after this many seconds instead of running until Ctrl-C",
    )
    args = parser.parse_args()
    try:
        asyncio.run(run(args.seconds))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
