"""LOGIN_MODE=stx: members sign in with their STX account, and that same
step connects it (the Playbook pattern). The app has no login of its own.

This is OpenID Connect on top of the connect flow:

1. ``GET /login``: ``Connect.start`` builds the STX URL with a ``state``,
   PKCE verifier and ``nonce``. We keep them server-side under the state and
   put only the state in the session cookie.
2. STX signs the member in (or signs them up) and asks them to allow this app.
3. ``GET /callback``: ``Connect.finish`` checks the state, exchanges the code
   and verifies the ID token. Its ``sub`` is the member's stable STX id for
   this app: we find or create our user on it and save their tokens.
"""

import time
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from stx import oauth

from sample.context import Context, ctx, redirect

router = APIRouter()

CONNECT_URL = "/login"

SIGN_IN_TTL = 600


def connect_client(c: Context) -> oauth.AsyncConnect:
    """One AsyncConnect for the app, built on first use."""
    if c.connect is None:
        c.connect = oauth.AsyncConnect(
            issuer=c.oauth.base_url,
            client_id=c.settings.client_id,
            client_secret=c.settings.client_secret,
            redirect_uri=c.settings.redirect_uri,
            scopes=c.settings.member_scopes,
        )
    return c.connect


@router.get("/login")
async def login(request: Request, connection: Optional[str] = None, login_hint: Optional[str] = None):
    c = ctx(request)
    if c.oauth is None:
        raise c.unavailable
    # connection="google" (or "apple", "x") goes straight to that provider.
    started = await connect_client(c).start(connection=connection, login_hint=login_hint)
    c.pending.put_raw(started.state, started.saved().to_dict(), time.time() + SIGN_IN_TTL)
    request.session["sign_in_state"] = started.state
    return RedirectResponse(started.url, status_code=303)


@router.get("/callback")
async def callback(request: Request):
    c = ctx(request)
    if c.oauth is None:
        raise c.unavailable
    state = request.session.pop("sign_in_state", None)
    saved = c.pending.take_raw(state) if state else None
    if saved is None:
        raise oauth.STXOAuthException("invalid_state", "No sign-in in progress in this browser; start again.")
    # Raises the callback's typed errors (declined, account pending, terms
    # not accepted) and invalid_state / invalid_id_token.
    done = await connect_client(c).finish(dict(request.query_params), oauth.SavedSignIn.from_dict(saved))
    who = done.identity
    user = c.db.user_by_sub(who.sub)
    user_id = user["id"] if user else c.db.create_user(who.email or "STX member", stx_sub=who.sub)
    c.tokens.set(str(user_id), done.tokens.to_stored())
    request.session["user_id"] = user_id
    return redirect("/dashboard", "Signed in with your STX account.")


async def close(context: Context) -> None:
    if context.connect is not None:
        await context.connect.close()
