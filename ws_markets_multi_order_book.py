"""Markets channel: multiple live order books.

Subscribes server-side to a category of markets via ``rule_filters``
and maintains a dict of order books keyed by ``market_id``. After each
update, prints the current top-of-book for every market we've seen so
far.

This is the efficient pattern when you want N order books that share a
rule type: the server only sends frames for matching markets, and the
client just routes by id. Frames are already dicts keyed by
``market_id``, so routing is a dict merge.

If you instead want a fixed list of specific market_ids across rule
types, drop ``rule_filters`` from the join payload and gate updates
client-side on ``WATCH``.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python ws_markets_multi_order_book.py
"""
import asyncio
import sys
from collections import Counter
from datetime import datetime
from typing import Dict, List

from stx.enums import Channels

from demo_config import make_ws

LISTEN_WINDOW_SECONDS = 20
RULE_FILTERS: List[str] = ["spread", "home_winner"]
WATCH: List[str] = []  # empty = render every market_id matching RULE_FILTERS
DEPTH = 3


books: Dict[str, dict] = {}


def _hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _top(side, label: str) -> str:
    if not side:
        return f"{label}=(empty)"
    rows = []
    for lvl in (side or [])[:DEPTH]:
        if isinstance(lvl, dict):
            price = lvl.get("price")
            size = lvl.get("quantity") or lvl.get("size")
            rows.append(f"{price}x{size}")
    return f"{label}=[{', '.join(rows)}]"


def _render_books() -> None:
    if not books:
        return
    print(f"\n  [{_hms()}] === {len(books)} books ===")
    for mid, book in sorted(books.items()):
        print(
            f"    {mid[:24]:<24}  "
            f"{_top(book.get('bids'), 'bids')}  "
            f"{_top(book.get('offers'), 'offers')}"
        )


async def stream() -> None:
    events: Counter = Counter()

    async def on_msg(msg) -> None:
        events[msg.event] += 1
        if msg.is_join_reply:
            r = (msg.payload or {}).get("response") or {}
            print(
                f"  [{_hms()}] join-reply  "
                f"selected_rule_filters={r.get('selected_rule_filters')}"
            )
            return
        if msg.is_reply:
            return
        changed = False
        for mid, m in (msg.payload or {}).items():
            if WATCH and mid not in WATCH:
                continue
            if "bids" not in m and "offers" not in m:
                continue  # a status tick with no book change
            books[mid] = {"bids": m.get("bids"), "offers": m.get("offers")}
            changed = True
        if changed:
            _render_books()

    async with make_ws() as ws:
        await ws.join(
            Channels.MARKETS,
            on_message=on_msg,
            join_params={
                "fields": ["bids", "offers"],
                "rule_filters": RULE_FILTERS,
            },
        )
        print(
            f"Tracking order books for {RULE_FILTERS} on Channels.MARKETS for "
            f"{LISTEN_WINDOW_SECONDS}s..."
        )
        try:
            await asyncio.wait_for(asyncio.Event().wait(), LISTEN_WINDOW_SECONDS)
        except asyncio.TimeoutError:
            pass

    print(
        f"\nReceived {events.get('market_updated', 0)} update frames across "
        f"{len(books)} unique markets in {LISTEN_WINDOW_SECONDS}s."
    )
    if not books:
        print(
            "  (no books; the environment may be quiet, or no markets match the rule filters)"
        )


def main() -> None:
    try:
        asyncio.run(stream())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
