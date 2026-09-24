"""Markets channel: server-side rule filtering.

Asks the server to only push updates for markets whose rule type is in
``RULE_FILTERS``. The join-reply echoes ``available_rules``, the full
list of rule names valid on the environment you're connected to, which makes
this a useful discovery script too.

Pass ``"rule_filters": null`` (or an empty list) at join time to
disable filtering, or do it dynamically with ``ws.push(...)``; see
``ws_markets_dynamic.py``.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python ws_markets_rule_filters.py
"""
import asyncio
import sys
from collections import Counter
from datetime import datetime

from stx.enums import Channels

from demo_config import make_ws

LISTEN_WINDOW_SECONDS = 20
RULE_FILTERS = ["spread", "home_winner"]


def _hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


async def stream() -> None:
    events: Counter = Counter()
    by_rule: Counter = Counter()
    received = 0

    async def on_msg(msg) -> None:
        nonlocal received
        events[msg.event] += 1
        if msg.is_join_reply:
            r = (msg.payload or {}).get("response") or {}
            available = r.get("available_rules") or []
            print(f"  [{_hms()}] join-reply")
            print(f"    selected_rule_filters={r.get('selected_rule_filters')}")
            print(f"    available_rules ({len(available)}): {available[:12]} ...")
            return
        if msg.is_reply:
            return
        # A market_created frame carries the full market, including its
        # `rules`; a market_updated frame carries only what changed, so
        # the rule is not repeated (the server has already filtered).
        for market_id, m in (msg.payload or {}).items():
            received += 1
            rules = m.get("rules")
            if isinstance(rules, str):
                by_rule[rules] += 1
            print(
                f"  [{_hms()}] {msg.event:<16} {market_id}  "
                f"rules={rules or '(not in frame)'}  title={m.get('title')!r}"
            )

    async with make_ws() as ws:
        await ws.join(
            Channels.MARKETS,
            on_message=on_msg,
            join_params={"rule_filters": RULE_FILTERS},
        )
        print(
            f"Listening for {RULE_FILTERS} markets on Channels.MARKETS for "
            f"{LISTEN_WINDOW_SECONDS}s..."
        )
        try:
            await asyncio.wait_for(asyncio.Event().wait(), LISTEN_WINDOW_SECONDS)
        except asyncio.TimeoutError:
            pass

    print(f"\nReceived {received} market updates in {LISTEN_WINDOW_SECONDS}s:")
    for event, count in sorted(events.items(), key=lambda x: -x[1]):
        print(f"  {event:<25} {count}")
    if by_rule:
        print("By rule type (market_created frames only):")
        for rule, count in sorted(by_rule.items(), key=lambda x: -x[1]):
            print(f"  {rule:<20} {count}")
    if not received:
        print(
            "  (no frames; the environment may be quiet, or no markets match the rule filters)"
        )


def main() -> None:
    try:
        asyncio.run(stream())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
