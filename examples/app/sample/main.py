"""The web app: routes shared by both login modes.

Run it with ``uvicorn sample.main:create_app --factory --port 8765`` from
``examples/app``. ``LOGIN_MODE`` picks the module that handles signing in
and connecting (``sample.login_stx`` or ``sample.login_own``); everything
else here is the same in both modes.
"""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

import stx
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from stx import oauth

from sample import live, login_own, login_stx
from sample.config import APP_SCOPE, Settings, load_settings
from sample.context import Context, ctx, current_user, is_connected, member_client, redirect, render
from sample.errors import describe
from sample.store import Database, PendingStore, TokenCipher, TokenStore

log = logging.getLogger("sample")

LOGIN_MODULES = {"stx": login_stx, "own": login_own}


async def build_oauth(settings: Settings) -> oauth.AsyncOAuthClient:
    """One OAuthClient for the app, from the exchange's discovery document.
    Raises STXNotAvailableError on an exchange without OAuth."""
    where: dict[str, Any] = (
        {"host": settings.host} if settings.host else {"region": settings.region, "env": settings.env}
    )
    return await oauth.AsyncOAuthClient.discover(
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        redirect_uri=settings.redirect_uri,
        scope=settings.member_scopes,
        **where,
    )


def create_app(settings: Optional[Settings] = None, *, oauth_client: Any = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s %(message)s")
    settings = settings or load_settings()
    cipher = TokenCipher(settings.token_encryption_key)
    if not cipher.enabled:
        log.warning("TOKEN_ENCRYPTION_KEY is not set: STX tokens are stored unencrypted.")
    if settings.session_secret == "change-me":
        log.warning("SESSION_SECRET is not set: session cookies are signed with a placeholder.")
    db = Database(settings.database, cipher)
    context = Context(
        settings=settings,
        db=db,
        tokens=TokenStore(db),
        pending=PendingStore(db),
        login=LOGIN_MODULES[settings.login_mode],
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            context.oauth = oauth_client or await build_oauth(settings)
            context.catalog = context.oauth.app_client(APP_SCOPE)
        except stx.STXNotAvailableError as exc:
            # The app still starts, and every page explains what is missing.
            context.unavailable = exc
            log.warning("%s", exc)
        yield
        if context.catalog is not None:
            await context.catalog.close()
        if context.oauth is not None and oauth_client is None:
            await context.oauth.close()
        await context.login.close(context)

    app = FastAPI(title="STX sample app", lifespan=lifespan)
    app.state.ctx = context
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret, same_site="lax")
    app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
    app.include_router(context.login.router)
    app.include_router(live.router)

    @app.exception_handler(NotConnected)
    async def not_connected(request: Request, exc: NotConnected):
        return RedirectResponse("/dashboard" if current_user(request) else "/", status_code=303)

    @app.exception_handler(stx.STXException)
    async def stx_error(request: Request, exc: stx.STXException):
        page = describe(
            exc,
            connect_url=context.login.CONNECT_URL,
            return_url=f"{settings.public_url}/dashboard",
        )
        log.info("showing %s for %s: %s", page.code, type(exc).__name__, exc)
        return render(request, "error.html", status_code=page.status, page=page)

    def require_oauth() -> None:
        if context.unavailable is not None:
            raise context.unavailable

    # ---- public pages ----------------------------------------------------

    @app.get("/healthz")
    async def healthz():
        return JSONResponse(
            {
                "ok": True,
                "login_mode": settings.login_mode,
                "exchange": context.oauth.host if context.oauth else None,
                "oauth": context.oauth is not None,
            }
        )

    @app.get("/")
    async def home(request: Request):
        return render(request, "home.html")

    @app.get("/markets")
    async def markets(request: Request):
        """The market list, read with the app's own token: no member needed."""
        require_oauth()
        page = await context.catalog.markets(status="open", trading=True, limit=25)
        return render(request, "markets.html", markets=page.items)

    @app.get("/markets/{market_id}")
    async def market(request: Request, market_id: str):
        require_oauth()
        found = await context.catalog.market(market_id)
        return render(request, "market.html", market=found)

    # ---- the member's account -------------------------------------------

    @app.get("/dashboard")
    async def dashboard(request: Request):
        require_oauth()
        user = current_user(request)
        if user is None:
            return RedirectResponse("/", status_code=303)
        if not is_connected(request, user):
            return render(request, "connect.html")
        async with member_client(request, user) as member:
            balance, positions, orders, fills, settlements = await asyncio.gather(
                section(member.balance()),
                section(member.positions()),
                section(member.orders(status="open", limit=25)),
                section(member.fills(limit=10)),
                section(member.settlements(limit=10)),
            )
        positions = (positions[0] and [p for p in positions[0] if nonzero(p.position)], positions[1])
        titles = await market_titles(context, [*ids(positions[0]), *ids(orders[0]), *ids(fills[0])])
        return render(
            request,
            "dashboard.html",
            balance=balance,
            positions=positions,
            orders=orders,
            fills=fills,
            settlements=settlements,
            titles=titles,
        )

    @app.post("/orders")
    async def place_order(
        request: Request,
        market_id: str = Form(...),
        action: str = Form(...),
        price: str = Form(...),
        quantity: str = Form(...),
    ):
        user = signed_in_and_connected(request)
        async with member_client(request, user) as member:
            order = await member.place_order(
                market_id,
                action,
                "limit",
                price=price,
                quantity=quantity,
                client_order_id=f"sample-{uuid.uuid4()}",
            )
        return redirect("/dashboard", f"Placed {action} {quantity} @ {price}: order {order.id} is {order.status}.")

    @app.post("/orders/{order_id}/cancel")
    async def cancel_order(request: Request, order_id: str):
        user = signed_in_and_connected(request)
        async with member_client(request, user) as member:
            result = await member.cancel_order(order_id)
        return redirect("/dashboard", f"Cancel requested for {order_id}: {result.status}.")

    @app.post("/unlink")
    async def unlink(request: Request):
        """Revoke the grant at STX and delete the tokens here."""
        require_oauth()
        user = current_user(request)
        if user is not None:
            await live.close_account_feeds(request, user)
            revoked = await context.oauth.unlink(context.tokens, str(user["id"]))
            return redirect("/", "Disconnected your STX account." if revoked else "Removed the STX connection here.")
        return RedirectResponse("/", status_code=303)

    @app.post("/logout")
    async def logout(request: Request):
        """Sign out of this app. The STX connection stays, ready for next time."""
        request.session.clear()
        return redirect("/", "Signed out.")

    return app


class NotConnected(Exception):
    """No signed-in user, or one with no STX connection: go and connect."""


def signed_in_and_connected(request: Request) -> dict[str, Any]:
    c = ctx(request)
    if c.unavailable is not None:
        raise c.unavailable
    user = current_user(request)
    if user is None or not is_connected(request, user):
        raise NotConnected()
    return user


async def section(call) -> tuple:
    """One dashboard section: (value, None), or (None, why) when the member
    did not allow the scope it needs. Anything else stops the page."""
    try:
        return await call, None
    except stx.STXInsufficientScopeException as exc:
        return None, f"Needs {' '.join(exc.required_scopes) or 'a scope you did not allow'}."


def nonzero(value: Optional[str]) -> bool:
    try:
        return Decimal(value or "0") != 0
    except InvalidOperation:
        return True


def ids(rows: Any) -> list[str]:
    if rows is None:
        return []
    items = getattr(rows, "items", rows)
    return [r.market_id for r in items if getattr(r, "market_id", None)]


async def market_titles(c: Context, market_ids: list[str]) -> dict[str, str]:
    """Market titles for the ids on the dashboard, from the app's catalog."""
    wanted = sorted(set(market_ids))[:50]
    if not wanted or c.catalog is None:
        return {}
    try:
        page = await c.catalog.markets(market_ids=wanted, limit=len(wanted))
    except stx.STXException:
        return {}
    return {m.market_id: m.title or m.symbol or m.market_id for m in page.items}
