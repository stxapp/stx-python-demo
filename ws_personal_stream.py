"""Stream your own portfolio + order updates over WebSocket.

Subscribes to the user-scoped channels: ``PORTFOLIO`` (balance / PnL
ticks) and ``ORDERS`` (status transitions on your resting orders).
Both auto-attach your user id as the topic scope; you don't construct
``"portfolio:<your-user-id>"`` strings yourself. One ``me()`` call at
startup is what supplies that id.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python ws_personal_stream.py

The script doesn't generate any activity itself. For a guaranteed
update on the ORDERS channel run ``safe_order_round_trip.py`` in a
second shell while this is listening.
"""
import asyncio
import sys

from stx.enums import Channels

from demo_config import make_client, make_ws

LISTEN_WINDOW_SECONDS = 20


async def stream() -> None:
    # There is no login response under API-key auth, so the user id the
    # per-user topics need has to be fetched once. me() seeds it for every
    # client in the process; do this before joining any scoped channel.
    with make_client() as client:
        me = client.me()
    print(f"Authenticated as {me.user_id}")

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
        # ORDERS, so join() auto-attaches `:<your-user-id>` to the wire topic.
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
