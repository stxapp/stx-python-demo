"""Markets channel — receive only ``market_updated`` events.

Asks the server to skip ``market_created`` broadcasts so you only get
ticks for already-listed markets. Useful for steady-state monitoring
when new listings landing mid-stream would be noise.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python ws_markets_message_types.py
"""
import asyncio
import sys
from collections import Counter
from datetime import datetime

from stx import STX, STXWebSocket
from stx.enums import Channels


LISTEN_WINDOW_SECONDS = 30


def _hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


async def stream() -> None:
    with STX(region="ontario", env="staging") as client:
        client.login(params={})

    events: Counter = Counter()
    received = 0

    async def on_msg(msg) -> None:
        nonlocal received
        events[msg.event] += 1
        if msg.is_join_reply:
            p = msg.payload or {}
            print(
                f"  [{_hms()}] join-reply  "
                f"selected_message_types={p.get('selected_message_types')}"
            )
            return
        received += 1
        p = msg.payload or {}
        print(
            f"  [{_hms()}] {msg.event:<18} "
            f"market_id={p.get('market_id')} title={p.get('title')!r}"
        )

    async with STXWebSocket(region="ontario", env="staging") as ws:
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

    print(f"\nReceived {received} updates in {LISTEN_WINDOW_SECONDS}s:")
    for event, count in sorted(events.items(), key=lambda x: -x[1]):
        print(f"  {event:<25} {count}")
    if not received:
        print("  (no frames — env may be quiet outside ET market hours)")


def main() -> None:
    try:
        asyncio.run(stream())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
