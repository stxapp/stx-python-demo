"""Markets channel: receive only ``market_updated`` events.

Asks the server to skip ``market_created`` broadcasts so you only get
ticks for already-listed markets. Useful for steady-state monitoring
when new listings landing mid-stream would be noise.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python ws_markets_message_types.py
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
            r = (msg.payload or {}).get("response") or {}
            print(
                f"  [{_hms()}] join-reply  "
                f"selected_message_types={r.get('selected_message_types')}"
            )
            return
        if msg.is_reply:
            return
        for market_id, fields in (msg.payload or {}).items():
            received += 1
            mandatory = ("market_id", "timestamp", "unix_timestamp")
            changed = sorted(k for k in fields if k not in mandatory)
            print(f"  [{_hms()}] {msg.event:<16} {market_id}  changed={changed}")

    async with make_ws() as ws:
        await ws.join(
            Channels.MARKETS,
            on_message=on_msg,
            join_params={"message_types": ["market_updated"]},
        )
        print(
            f"Listening (market_updated only) on Channels.MARKETS for "
            f"{LISTEN_WINDOW_SECONDS}s..."
        )
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
