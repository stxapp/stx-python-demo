"""Stream your own fills over WebSocket: the ``TRADES`` channel.

Subscribes to the per-user ``active_trades:<user_id>`` topic and prints
every fill as it lands. This replaces polling ``client.trades()`` in a
bot that needs to know the moment an order executes.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python ws_trades_stream.py

The script places no orders itself, so on a quiet account the window
ends with zero fills. That is the expected outcome; the join reply
confirms the subscription is live.
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
    # Per-user topics are keyed on your user id, and with no login
    # response to read it from, one me() call at startup supplies it.
    with make_client() as client:
        me = client.me()
    print(f"Authenticated as {me.user_id}")

    fills = 0

    async def on_trade(msg) -> None:
        nonlocal fills
        if msg.is_join_reply:
            print(f"  [{_hms()}] join-reply  status={msg.reply_status}")
            return
        if msg.is_reply:
            return
        p = msg.payload or {}
        if msg.event == "all_trades":
            # Snapshot sent once on join: your trades on still-active markets.
            print(f"  [{_hms()}] snapshot    {len(p.get('trades') or [])} active trade(s)")
            return
        fills += 1
        print(
            f"  [{_hms()}] {msg.event:<16} "
            f"market_id={p.get('market_id')} action={p.get('action')} "
            f"px={p.get('price')} filled={p.get('filled')}"
        )

    async with make_ws() as ws:
        await ws.join(Channels.TRADES, on_message=on_trade)
        print(f"Listening on Channels.TRADES for {LISTEN_WINDOW_SECONDS}s...")
        try:
            await asyncio.wait_for(asyncio.Event().wait(), LISTEN_WINDOW_SECONDS)
        except asyncio.TimeoutError:
            pass

    print(f"\nReceived {fills} fill frame(s) in {LISTEN_WINDOW_SECONDS}s.")
    if not fills:
        print(
            "  (none: nothing of yours executed during the window. A resting "
            "order that crosses the book would show up here.)"
        )


def main() -> None:
    try:
        asyncio.run(stream())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
