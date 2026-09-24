"""Markets channel: narrow fields to bids and offers.

Server-side filter via the join-payload ``fields`` list: only the
liquidity-relevant keys come back, plus the always-on mandatory
``market_id`` / ``timestamp`` / ``unix_timestamp``.

Useful when you only need order-book information and want to keep
frame sizes small. The payload is a dict keyed by ``market_id``.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python ws_markets_bids_offers.py
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


def _depth(side, label: str) -> str:
    if not side:
        return f"{label}=(empty)"
    rows = []
    for lvl in (side or [])[:3]:
        if isinstance(lvl, dict):
            rows.append(f"{lvl.get('price')}x{lvl.get('quantity') or lvl.get('size')}")
    return f"{label}=[{', '.join(rows)}]"


async def stream() -> None:
    events: Counter = Counter()
    received = 0

    async def on_msg(msg) -> None:
        nonlocal received
        events[msg.event] += 1
        if msg.is_join_reply:
            # The reply nests the effective configuration under "response".
            r = (msg.payload or {}).get("response") or {}
            print(f"  [{_hms()}] join-reply  status={msg.reply_status} config={sorted(r)}")
            return
        if msg.is_reply:
            return
        for market_id, m in (msg.payload or {}).items():
            if "bids" not in m and "offers" not in m:
                continue  # a trading/status tick with no book change
            received += 1
            print(
                f"  [{_hms()}] {msg.event:<16} {market_id}  "
                f"{_depth(m.get('bids'), 'bids')}  {_depth(m.get('offers'), 'offers')}"
            )

    async with make_ws() as ws:
        await ws.join(
            Channels.MARKETS,
            on_message=on_msg,
            join_params={"fields": ["bids", "offers"]},
        )
        print(
            f"Listening for bids/offers on Channels.MARKETS for "
            f"{LISTEN_WINDOW_SECONDS}s..."
        )
        try:
            await asyncio.wait_for(asyncio.Event().wait(), LISTEN_WINDOW_SECONDS)
        except asyncio.TimeoutError:
            pass

    print(f"\nReceived {received} book updates in {LISTEN_WINDOW_SECONDS}s:")
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
