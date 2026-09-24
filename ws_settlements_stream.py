"""Stream your own settlements over WebSocket: the ``SETTLEMENTS`` channel.

Subscribes to the per-user ``active_settlements:<user_id>`` topic and
prints a frame each time one of your positions settles. Pair it with
``history_pulls.py``, which reads the same data after the fact.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python ws_settlements_stream.py

Settlements happen when a market resolves, so the window usually ends
with zero frames. That is the expected outcome; the join reply confirms
the subscription is live.
"""
import asyncio
import sys
from datetime import datetime

from stx.enums import Channels

from demo_config import make_client, make_ws

LISTEN_WINDOW_SECONDS = 20


def _hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


async def stream() -> None:
    # One me() call seeds the user id the scoped topic is built from.
    with make_client() as client:
        me = client.me()
    print(f"Authenticated as {me.user_id}")

    frames = 0

    async def on_settlement(msg) -> None:
        nonlocal frames
        if msg.is_join_reply:
            print(f"  [{_hms()}] join-reply  status={msg.reply_status}")
            return
        if msg.is_reply:
            return
        p = msg.payload or {}
        if msg.event == "all_settlements":
            print(f"  [{_hms()}] snapshot    {len(p.get('settlements') or [])} settlement(s)")
            return
        frames += 1
        print(
            f"  [{_hms()}] {msg.event:<20} "
            f"market_id={p.get('market_id')} type={p.get('type')} "
            f"qty={p.get('quantity')} pnl={p.get('realized_pnl')} fee={p.get('fee')}"
        )

    async with make_ws() as ws:
        await ws.join(Channels.SETTLEMENTS, on_message=on_settlement)
        print(f"Listening on Channels.SETTLEMENTS for {LISTEN_WINDOW_SECONDS}s...")
        try:
            await asyncio.wait_for(asyncio.Event().wait(), LISTEN_WINDOW_SECONDS)
        except asyncio.TimeoutError:
            pass

    print(f"\nReceived {frames} settlement frame(s) in {LISTEN_WINDOW_SECONDS}s.")
    if not frames:
        print("  (none: no market you hold a position in resolved during the window.)")


def main() -> None:
    try:
        asyncio.run(stream())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
