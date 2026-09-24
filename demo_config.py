"""Shared setup for every script in this repo.

Each example builds its client through this module so that they all
agree on three things:

1. **Where to connect.** The SDK reads ``STX_REGION`` / ``STX_ENV`` (or
   ``STX_HOST``) from the environment. When none of them is set, the
   scripts default to the public US demo environment (``region="us"``,
   ``env="demo"``), which uses no real money. Nothing is hardcoded in
   the individual scripts, so setting an environment variable is enough
   to point every example somewhere else.

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

``make_async_client()`` and ``make_ws()`` do the same for ``AsyncSTX``
and ``STXWebSocket``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from stx import STX, AsyncSTX, STXWebSocket

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
    """Resolve the connection kwargs shared by all three client classes.

    ``STX_HOST`` wins outright. Otherwise ``STX_REGION`` / ``STX_ENV`` are
    used, each falling back to the US demo default when unset.
    """
    load_dotenv()
    host = os.getenv("STX_HOST")
    if host:
        return {"host": host}
    region = (os.getenv("STX_REGION") or DEFAULT_REGION).lower()
    env = (os.getenv("STX_ENV") or DEFAULT_ENV).lower()
    return {"region": region, "env": env}


def describe_target() -> str:
    """Human-readable form of the target, for banner lines."""
    kwargs = connection_kwargs()
    if "host" in kwargs:
        return kwargs["host"]
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


def make_ws(**kwargs) -> STXWebSocket:
    """WebSocket client for the configured environment."""
    return _build(STXWebSocket, **kwargs)
