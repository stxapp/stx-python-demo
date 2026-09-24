"""Stream the ``user_info`` channel: your profile, then any change to it.

``user_updated`` arrives right after joining with the current profile,
and again whenever it changes (status, limits, contact details).

Run:
    python ws_user_info.py
    python ws_user_info.py --seconds 60
"""

import asyncio

from demo_config import listen, make_async_client, seconds_arg


def show(msg) -> str:
    return f"status {msg.payload['userStatus']}"


async def main(seconds: float) -> None:
    async with make_async_client() as client:
        async with client.websocket() as ws:
            info = await ws.user_info()
            print(f"Joined {info.topic}: {info.reply}")
            profile = (await info.wait_snapshot())["user_updated"]
            print(
                f"Status {profile['userStatus']}, test account {profile['test_account']}, country "
                f"{profile['country']}"
            )
            await info.next(timeout=5)
            await listen(info, seconds, show)


if __name__ == "__main__":
    asyncio.run(main(seconds_arg(20.0, __doc__.splitlines()[0])))
