"""Stream your ``orders`` channel: every accepted, filled or cancelled order.

``all_orders`` arrives on join with your open orders, then
``new_open_order`` carries the whole order each time it changes. To have
something to show, the script places a resting 1-cent buy (demo only,
never fills) and cancels it, printing both pushes. Pass ``--no-order``
to only listen.

With ``--cancel-on-disconnect`` it arms cancel-on-disconnect on the join;
the SDK then pings the channel at 60% of the timeout the server grants.

Run:
    python ws_orders.py
    python ws_orders.py --no-order --seconds 60
"""

import argparse
import asyncio

from demo_config import find_tradeable_market, listen, make_async_client, make_client


def show(msg) -> str:
    p = msg.payload
    return f"{p['id']} {p['status']:<10} {p['action']} {p['filled']}/{p['quantity']} @ {p['price']}"


async def main(args) -> None:
    market = None
    if not args.no_order:
        with make_client() as sync_client:
            market = find_tradeable_market(sync_client)

    async with make_async_client() as client:
        async with client.websocket() as ws:
            orders = await ws.orders(cancel_on_disconnect=args.cancel_on_disconnect)
            print(f"Joined {orders.topic}: {orders.reply}")
            snapshot = (await orders.wait_snapshot())["all_orders"]["orders"]
            print(f"Snapshot: {len(snapshot)} open order(s)")
            await orders.next(timeout=5)  # the snapshot message itself

            if market is not None:
                order = await client.place_order(
                    market.market_id, "buy", "limit", price="0.01", quantity="1"
                )
                print(f"Placed {order.id} on {market.symbol}; cancelling...")
                await client.cancel_order(order.id)
            await listen(orders, args.seconds, show)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--no-order", action="store_true", help="only listen")
    parser.add_argument("--cancel-on-disconnect", action="store_true")
    asyncio.run(main(parser.parse_args()))
