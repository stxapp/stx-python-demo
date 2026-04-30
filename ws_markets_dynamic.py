"""Markets channel — change filters mid-stream.

Joins with one filter, then mid-stream uses ``ws.push(...)`` to swap
the field selection and disable rule filtering — without re-joining.

Three dynamic events are supported post-join:

- ``select_fields`` — replace the field list
- ``select_rule_filters`` — replace the rule filter list (``null`` to disable)
- ``select_message_types`` — replace the message-type list

Each one is fire-and-forget; the server replies with the new effective
config on the same channel.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python ws_markets_dynamic.py
"""
import asyncio
import sys
from collections import Counter
from datetime import datetime

from stx import STX, STXWebSocket
from stx.enums import Channels


LISTEN_WINDOW_SECONDS = 25
SWAP_AT_SECONDS = 10


def _hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


async def stream() -> None:
    with STX(region="ontario", env="staging") as client:
        client.login()

    events: Counter = Counter()

    async def on_msg(msg) -> None:
        events[msg.event] += 1
        if msg.is_join_reply:
            p = msg.payload or {}
            print(
                f"  [{_hms()}] join-reply  "
                f"selected_fields={p.get('selected_fields')} "
                f"selected_rule_filters={p.get('selected_rule_filters')}"
            )
            return
        if msg.event == "phx_reply":
            print(
                f"  [{_hms()}] phx_reply   "
                f"status={msg.reply_status} payload={msg.payload}"
            )
            return
        p = msg.payload or {}
        keys = sorted(k for k in (p or {}).keys() if k not in ("market_id", "title"))
        print(
            f"  [{_hms()}] {msg.event:<18} "
            f"market_id={p.get('market_id')} fields_present={keys}"
        )

    async with STXWebSocket(region="ontario", env="staging") as ws:
        await ws.join(
            Channels.MARKETS,
            on_message=on_msg,
            join_params={
                "fields": ["bids", "offers"],
                "rule_filters": ["spread"],
            },
        )
        print(
            f"Listening on Channels.MARKETS for {LISTEN_WINDOW_SECONDS}s; "
            f"swapping filters at +{SWAP_AT_SECONDS}s..."
        )

        async def swap_filters() -> None:
            await asyncio.sleep(SWAP_AT_SECONDS)
            print(f"\n  [{_hms()}] >>> push select_fields(['title','price','recent_trades'])")
            await ws.push(
                Channels.MARKETS,
                "select_fields",
                {"fields": ["title", "price", "recent_trades"]},
            )
            await asyncio.sleep(2)
            print(f"  [{_hms()}] >>> push select_rule_filters(null) — disable filtering\n")
            await ws.push(
                Channels.MARKETS, "select_rule_filters", {"rule_filters": None}
            )

        swap_task = asyncio.create_task(swap_filters())
        try:
            await asyncio.wait_for(asyncio.Event().wait(), LISTEN_WINDOW_SECONDS)
        except asyncio.TimeoutError:
            pass
        swap_task.cancel()

    print(f"\nFrame counts in {LISTEN_WINDOW_SECONDS}s:")
    for event, count in sorted(events.items(), key=lambda x: -x[1]):
        print(f"  {event:<25} {count}")


def main() -> None:
    try:
        asyncio.run(stream())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
