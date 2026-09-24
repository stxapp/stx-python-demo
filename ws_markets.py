"""Stream the ``markets`` channel: market metadata as it changes, for every market.

Pushes ``market_created`` (the full market) and ``market_updated`` (the
market id, timestamps and only the fields that changed). Each payload
maps market id to market object. The wire sends prices in cents on this
channel; the SDK converts them to dollar strings, so ``price`` reads
"0.4200" here the same as everywhere else.

Filters: ``rule_filters`` (market rules, e.g. ``home_winner``) and
``message_types``; ``select_rule_filters`` / ``select_message_types``
change them without rejoining.

Run:
    python ws_markets.py
    python ws_markets.py --seconds 60
"""

import asyncio

from demo_config import listen, make_async_client, seconds_arg


def show(msg) -> str:
    parts = []
    for market_id, change in msg.payload.items():
        fields = {
            k: v for k, v in change.items() if k not in ("market_id", "timestamp", "unix_timestamp")
        }
        parts.append(f"{market_id} {fields}")
    return "; ".join(parts)[:220]


async def main(seconds: float) -> None:
    async with make_async_client() as client:
        async with client.websocket() as ws:
            markets = await ws.markets()
            print(
                f"Joined markets; {len(markets.reply['available_rules'])} rules available to "
                "filter on"
            )
            reply = await markets.select_message_types(["market_updated"])
            print(f"Now receiving: {reply['selected_message_types']}")
            await listen(markets, seconds, show)


if __name__ == "__main__":
    asyncio.run(main(seconds_arg(20.0, __doc__.splitlines()[0])))
