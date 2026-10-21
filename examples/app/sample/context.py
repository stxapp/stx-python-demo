"""What every route shares: settings, the database, the SDK clients, and
small helpers for the signed-in user."""

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Optional
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from stx import AsyncSTX
from stx.oauth import AsyncConnect, AsyncOAuthClient

from sample.config import Settings
from sample.store import Database, PendingStore, TokenStore

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@dataclass
class Context:
    settings: Settings
    db: Database
    tokens: TokenStore
    pending: PendingStore
    # The per-mode module (sample.login_own or sample.login_stx).
    login: ModuleType
    # One OAuthClient for the app, built from the exchange's discovery
    # document. None when the exchange offers no OAuth (see `unavailable`).
    oauth: Optional[AsyncOAuthClient] = None
    # The app acting as itself (client_credentials, scope market_data).
    catalog: Optional[AsyncSTX] = None
    # Why OAuth is missing on this exchange: an STXNotAvailableError.
    unavailable: Optional[Exception] = None
    # LOGIN_MODE=stx: Sign in with STX (OpenID Connect), built on first use.
    connect: Optional[AsyncConnect] = None


def ctx(request: Request) -> Context:
    return request.app.state.ctx


def current_user(request: Request) -> Optional[dict[str, Any]]:
    user_id = request.session.get("user_id")
    return ctx(request).db.user(int(user_id)) if user_id else None


def member_key(user: dict[str, Any]) -> str:
    """The key the SDK stores this user's STX tokens under: our own user id."""
    return str(user["id"])


def is_connected(request: Request, user: Optional[dict[str, Any]]) -> bool:
    return user is not None and ctx(request).tokens.get(member_key(user)) is not None


def member_client(request: Request, user: dict[str, Any]) -> AsyncSTX:
    """An ``AsyncSTX`` acting for this member. The SDK attaches their access
    token, refreshes it when due and saves the rotated pair in our store."""
    c = ctx(request)
    if c.oauth is None:
        raise c.unavailable or RuntimeError("OAuth is not set up")
    return c.oauth.member_client(c.tokens, member_key(user))


def render(request: Request, template: str, status_code: int = 200, **values: Any):
    user = current_user(request)
    c = ctx(request)
    values.setdefault("user", user)
    values.setdefault("connected", is_connected(request, user))
    values.setdefault("mode", c.settings.login_mode)
    values.setdefault("connect_url", c.login.CONNECT_URL)
    values.setdefault(
        "exchange", c.oauth.host if c.oauth else (c.settings.host or f"{c.settings.region} {c.settings.env}")
    )
    values.setdefault("message", request.query_params.get("msg"))
    return TEMPLATES.TemplateResponse(request, template, values, status_code=status_code)


def redirect(path: str, msg: Optional[str] = None) -> RedirectResponse:
    """A 303 to ``path``, with a one-line message the page shows."""
    return RedirectResponse(f"{path}?msg={quote(msg)}" if msg else path, status_code=303)
