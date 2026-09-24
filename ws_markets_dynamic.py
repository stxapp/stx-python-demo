"""Markets channel: change filters mid-stream.

Joins with one filter, then mid-stream uses ``ws.push(...)`` to change
the subscription without re-joining. Three control events exist:

- ``select_message_types``: replace the message-type list
- ``select_rule_filters``: replace the rule filter list (``null`` to disable)
- ``select_fields``: replace the field list

Each one is fire-and-forget; the server answers with a ``phx_reply``
carrying the new effective config on the same channel. This script
exercises the first two. The field list is set at join time here (see
``ws_markets_bids_offers.py``); ``select_fields`` follows the same push
pattern.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python ws_markets_dynamic.py
"""
import asyncio
import sys
from collections import Counter
from datetime import datetime

from stx.enums import Channels

from demo_config import make_ws

LISTEN_WINDOW_SECONDS = 20
SWAP_AT_SECONDS = 8


def _hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


async def stream() -> None:
    events: Counter = Counter()
    joined = False

    async def on_msg(msg) -> None:
        nonlocal joined
        events[msg.event] += 1
        r = (msg.payload or {}).get("response") or {}
        if msg.is_reply and not joined:
            joined = True
            print(
                f"  [{_hms()}] join-reply  "
                f"selected_rule_filters={r.get('selected_rule_filters')} "
                f"selected_message_types={r.get('selected_message_types')}"
            )
            return
        if msg.is_reply:
            # Reply to a push: the server echoes the setting that changed.
            print(f"  [{_hms()}] phx_reply   status={msg.reply_status} {r}")
            return
        if msg.is_error:
            print(f"  [{_hms()}] phx_error   {msg.payload}")
            return
        for market_id, m in (msg.payload or {}).items():
            print(f"  [{_hms()}] {msg.event:<16} {market_id}  rules={m.get('rules')}")

    async with make_ws() as ws:
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
            f"changing the subscription at +{SWAP_AT_SECONDS}s..."
        )

        async def swap_filters() -> None:
            await asyncio.sleep(SWAP_AT_SECONDS)
            print(f"\n  [{_hms()}] >>> push select_message_types(['market_updated'])")
            await ws.push(
                Channels.MARKETS,
                "select_message_types",
                {"message_types": ["market_updated"]},
            )
            await asyncio.sleep(2)
            print(f"  [{_hms()}] >>> push select_rule_filters(null) to disable filtering\n")
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
