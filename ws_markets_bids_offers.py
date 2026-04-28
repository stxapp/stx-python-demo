"""Markets channel — narrow fields to bids and offers.

Server-side filter via the join-payload ``fields`` list — only the
liquidity-relevant keys come back, plus the always-on mandatory
``market_id`` / ``timestamp`` / ``unix_timestamp``.

Useful when you only need order-book information and want to keep
frame sizes small.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python ws_markets_bids_offers.py
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


def _depth(side, label: str) -> str:
    if not side:
        return f"{label}=(empty)"
    rows = []
    for lvl in (side or [])[:3]:
        if isinstance(lvl, dict):
            rows.append(f"{lvl.get('price')}x{lvl.get('quantity') or lvl.get('size')}")
    return f"{label}=[{', '.join(rows)}]"


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
                f"  [{_hms()}] join-reply  selected_fields={p.get('selected_fields')}"
            )
            return
        received += 1
        p = msg.payload or {}
        print(
            f"  [{_hms()}] {msg.event:<18} "
            f"market_id={p.get('market_id')}  "
            f"{_depth(p.get('bids'), 'bids')}  {_depth(p.get('offers'), 'offers')}"
        )

    async with STXWebSocket(region="ontario", env="staging") as ws:
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
