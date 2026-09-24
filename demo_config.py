"""Shared setup for every script in this repo.

Each example builds its client through this module so that they all
agree on three things:

1. **Where to connect.** The SDK reads ``STX_REGION`` / ``STX_ENV`` (or
   ``STX_HOST``) from the environment, or the profile named by
   ``STX_PROFILE``. When none of them is set, the scripts default to the
   public US demo environment (``region="us"``, ``env="demo"``), which
   uses no real money. Nothing is hardcoded in the individual scripts,
   so setting an environment variable is enough to point every example
   somewhere else.

2. **Credentials.** ``STX_KEY_ID`` / ``STX_PRIVATE_KEY`` are read by the
   SDK itself and every request is signed with them; there is no login
   call. This module only checks that they are present and prints a
   short, readable message (instead of a traceback) when they are not.
   If ``STX_PROFILE`` names a profile in ``~/.stx/credentials`` the
   check is skipped and the SDK reads the key from there.

3. **The ``.env`` file.** If a ``.env`` file sits next to this module it
   is loaded into the process environment before anything else runs.
   Variables already set in your shell win over the file.

Usage from a script::

    from demo_config import make_client

    with make_client() as client:
        me = client.me()
        ...

``make_async_client()`` does the same for ``AsyncSTX``; open a socket
with ``client.websocket()`` on an async client. ``find_tradeable_market``,
``open_market_ids``, ``listen`` and ``seconds_arg`` are small helpers the
scripts share.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from stx import STX, AsyncSTX, Channel, ChannelMessage

DEFAULT_REGION = "us"
DEFAULT_ENV = "demo"

_ENV_FILE = Path(__file__).resolve().parent / ".env"

_MISSING_CREDENTIALS_MESSAGE = """\
No STX API key found.

These examples read STX_KEY_ID and STX_PRIVATE_KEY from the environment.
Create a key under Account, API Keys in the STX app, save the private
key to a file such as ~/.stx/us-demo.pem, then either export the two
variables in your shell or copy .env.example to .env next to the
scripts and fill them in. Accounts for the demo environment are free to
create at https://demo.stxapp.io and use no real money. The README's
Configuration section lists every variable.
"""


def load_dotenv(path: Path = _ENV_FILE) -> None:
    """Load ``KEY=VALUE`` lines from ``path`` into ``os.environ``.

    Deliberately tiny so the demos need no extra dependency: blank lines
    and ``#`` comments are skipped, surrounding quotes are stripped, and
    variables that are already set are left alone.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def require_credentials() -> None:
    """Exit with a friendly message if no API key is configured."""
    load_dotenv()
    if os.getenv("STX_PROFILE"):
        return
    if os.getenv("STX_KEY_ID") and os.getenv("STX_PRIVATE_KEY"):
        return
    print(_MISSING_CREDENTIALS_MESSAGE, file=sys.stderr)
    raise SystemExit(1)


def connection_kwargs() -> dict:
    """Resolve the connection kwargs shared by both client classes.

    ``STX_HOST`` wins outright. A profile (``STX_PROFILE``) with no region
    or env variables set decides for itself. Otherwise ``STX_REGION`` /
    ``STX_ENV`` are used, each falling back to the US demo default.
    """
    load_dotenv()
    host = os.getenv("STX_HOST")
    if host:
        return {"host": host}
    if os.getenv("STX_PROFILE") and not (os.getenv("STX_REGION") or os.getenv("STX_ENV")):
        return {}
    region = (os.getenv("STX_REGION") or DEFAULT_REGION).lower()
    env = (os.getenv("STX_ENV") or DEFAULT_ENV).lower()
    return {"region": region, "env": env}


def describe_target() -> str:
    """Human-readable form of the target, for banner lines."""
    kwargs = connection_kwargs()
    if "host" in kwargs:
        return kwargs["host"]
    if not kwargs:
        return f"profile {os.getenv('STX_PROFILE')}"
    return f"{kwargs['region']}/{kwargs['env']}"


def _build(cls, **extra):
    require_credentials()
    return cls(**connection_kwargs(), **extra)


def make_client(**kwargs) -> STX:
    """Synchronous HTTP client for the configured environment."""
    return _build(STX, **kwargs)


def make_async_client(**kwargs) -> AsyncSTX:
    """Async HTTP client for the configured environment."""
    return _build(AsyncSTX, **kwargs)


def find_tradeable_market(client: STX):
    """An open, trading market whose event has not started, or ``None``.

    Sorting by event start, latest first, puts far-future events at the
    top, so the first page almost always has one.
    """
    for market in client.iter_markets(
        status="open", trading=True, sort_by="event_start", sort_direction="desc"
    ):
        if market.event_status == "scheduled":
            return market
    return None


async def open_market_ids(client: AsyncSTX, count: int = 5) -> List[str]:
    """Ids of up to ``count`` open markets, for channels that need some."""
    page = await client.markets(status="open", trading=True, limit=count)
    return [m.market_id for m in page]


def seconds_arg(default: float = 20.0, doc: Optional[str] = None) -> float:
    """Parse ``--seconds N`` from the command line."""
    parser = argparse.ArgumentParser(description=doc)
    parser.add_argument(
        "--seconds",
        type=float,
        default=default,
        help=f"how long to listen (default {default:g})",
    )
    return parser.parse_args().seconds


def hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


async def listen(
    channel: Channel,
    seconds: float,
    show: Callable[[ChannelMessage], str],
    limit: int = 20,
) -> int:
    """Print up to ``limit`` messages from ``channel`` for ``seconds``.

    Returns how many arrived. ``show`` turns one message into a line.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds
    count = 0
    while count < limit:
        remaining = deadline - loop.time()
        if remaining <= 0:
            break
        try:
            msg = await channel.next(timeout=remaining)
        except asyncio.TimeoutError:
            break
        count += 1
        print(f"  [{hms()}] {msg.event:<22} {show(msg)}")
    if count == 0:
        print(
            f"  (nothing arrived on {channel.name} in {seconds:g}s; the demo exchange can be quiet)"
        )
    return count
