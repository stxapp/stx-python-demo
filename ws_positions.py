"""Stream your ``positions`` channel: open positions, then the ones that change.

``all_positions`` on join; ``updated_positions`` afterwards carries only
the positions that changed. ``position`` is positive when long and
negative when short. Positions are not marked to market: value them
against the order book yourself.

Run:
    python ws_positions.py
    python ws_positions.py --seconds 60
"""

import asyncio

from demo_config import listen, make_async_client, seconds_arg


def show(msg) -> str:
    return ", ".join(f"{p['market_id']} {p['position']}" for p in msg.payload["positions"])[:220]


async def main(seconds: float) -> None:
    async with make_async_client() as client:
        async with client.websocket() as ws:
            positions = await ws.positions()
            print(f"Joined {positions.topic}: {positions.reply}")
            held = (await positions.wait_snapshot())["all_positions"]["positions"]
            nonzero = [p for p in held if p["position"] != "0.00"]
            print(f"Snapshot: {len(held)} position record(s), {len(nonzero)} non-zero")
            for p in nonzero[:5]:
                print(
                    f"  {p['market_id']} net {p['position']} premium {p['premium']} open risk "
                    f"{p['open_risk']}"
                )
            await positions.next(timeout=5)
            await listen(positions, seconds, show)


if __name__ == "__main__":
    asyncio.run(main(seconds_arg(20.0, __doc__.splitlines()[0])))
