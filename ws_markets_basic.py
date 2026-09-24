"""Markets channel: hello-world listener.

Joins the broadcast ``markets`` topic with no filters and prints every
frame for ``LISTEN_WINDOW_SECONDS``. The default join asks the server
for every optional field, no rule filtering, and both
``market_updated`` + ``market_created`` events.

Frame shape: the payload is a dict keyed by ``market_id``, one entry
per market in the frame, and each value carries only the fields that
changed (plus the mandatory ``market_id`` / ``timestamp`` /
``unix_timestamp``). Iterate ``payload.items()`` to get at them.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python ws_markets_basic.py
"""
import asyncio
import sys
from collections import Counter
from datetime import datetime

from stx.enums import Channels

from demo_config import make_ws

LISTEN_WINDOW_SECONDS = 20


def _hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


async def stream() -> None:
    events: Counter = Counter()
    received = 0

    async def on_msg(msg) -> None:
        nonlocal received
        events[msg.event] += 1
        if msg.is_join_reply:
            print(f"  [{_hms()}] join-reply  status={msg.reply_status}")
            return
        if msg.is_reply:
            return
        for market_id, fields in (msg.payload or {}).items():
            received += 1
            mandatory = ("market_id", "timestamp", "unix_timestamp")
            changed = sorted(k for k in fields if k not in mandatory)
            print(f"  [{_hms()}] {msg.event:<16} {market_id}  changed={changed}")

    async with make_ws() as ws:
        await ws.join(Channels.MARKETS, on_message=on_msg)
        print(f"Listening on Channels.MARKETS for {LISTEN_WINDOW_SECONDS}s...")
        try:
            await asyncio.wait_for(asyncio.Event().wait(), LISTEN_WINDOW_SECONDS)
        except asyncio.TimeoutError:
            pass

    print(f"\nReceived {received} market updates in {LISTEN_WINDOW_SECONDS}s:")
    for event, count in sorted(events.items(), key=lambda x: -x[1]):
        print(f"  {event:<25} {count}")
    if not received:
        print("  (no frames; the environment may be quiet when no events are in play)")


def main() -> None:
    try:
        asyncio.run(stream())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
