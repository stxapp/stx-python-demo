"""Stream your own portfolio + order updates over WebSocket.

Subscribes to the user-scoped channels: ``PORTFOLIO`` (balance / PnL
ticks) and ``ORDERS`` (status transitions on your resting orders).
Both auto-attach your uid as the topic scope; you don't construct
``"portfolio:<your-uid>"`` strings yourself.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python ws_personal_stream.py

The script doesn't generate any activity itself. For a guaranteed
update on the ORDERS channel run ``safe_order_round_trip.py`` in a
second shell while this is listening.
"""
import asyncio
import sys

from stx.enums import Channels

from demo_config import make_client, make_ws

LISTEN_WINDOW_SECONDS = 30


async def stream() -> None:
    # Seed the User singleton: STXWebSocket needs the JWT but doesn't
    # log in on its own.
    with make_client() as client:
        client.login()

    portfolio_frames = []
    order_frames = []

    async def on_portfolio(msg) -> None:
        portfolio_frames.append(msg)
        print(f"  [PORTFOLIO] {msg.event}  {msg.payload}")

    async def on_order(msg) -> None:
        order_frames.append(msg)
        print(f"  [ORDERS]    {msg.event}  {msg.payload}")

    async with make_ws() as ws:
        # Per-user channels: `SCOPED_CHANNELS` includes PORTFOLIO and
        # ORDERS, so join() auto-attaches `:<your-uid>` to the wire topic.
        await ws.join(Channels.PORTFOLIO, on_message=on_portfolio)
        await ws.join(Channels.ORDERS, on_message=on_order)

        print(f"Listening for {LISTEN_WINDOW_SECONDS}s on PORTFOLIO + ORDERS...")
        try:
            await asyncio.wait_for(asyncio.Event().wait(), LISTEN_WINDOW_SECONDS)
        except asyncio.TimeoutError:
            pass

    print(
        f"\nReceived: {len(portfolio_frames)} portfolio, "
        f"{len(order_frames)} order frame(s)."
    )
    if not portfolio_frames and not order_frames:
        print(
            "  (none: your account had no orders / balance changes "
            "during the window. Run safe_order_round_trip.py in a "
            "second shell to trigger an ORDERS frame.)"
        )


def main() -> None:
    try:
        asyncio.run(stream())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
