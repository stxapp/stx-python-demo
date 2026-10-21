"""LOGIN_MODE=own: members sign in to this app with its own login, then
connect their STX account (the Sideline pattern).

The login here is a stand-in for yours: a name and no password. What
matters is the connect flow:

1. ``GET /connect``: ``begin_authorization`` saves a PKCE verifier and our
   user id under a fresh ``state`` and returns the STX URL to send them to.
2. STX signs the member in and asks them to allow this app.
3. ``GET /callback``: ``read_callback`` uses up the ``state``; we check the
   sign-in was started by this browser's user, then ``redeem_authorization``
   exchanges the code and saves the tokens under our user id.
"""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from stx import oauth

from sample.context import Context, ctx, current_user, redirect, render

router = APIRouter()

# Where the error pages send a member to connect (again).
CONNECT_URL = "/connect"


@router.get("/login")
async def login_page(request: Request):
    return render(request, "login_own.html")


@router.post("/login")
async def login(request: Request, name: str = Form(...)):
    db = ctx(request).db
    name = name.strip()[:40] or "member"
    user = db.user_by_name(name)
    user_id = user["id"] if user else db.create_user(name)
    request.session.clear()
    request.session["user_id"] = user_id
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/connect")
async def connect(request: Request):
    c = ctx(request)
    user = current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if c.oauth is None:
        raise c.unavailable
    auth = await c.oauth.begin_authorization(c.pending, data={"user_id": user["id"]})
    return RedirectResponse(auth.url, status_code=303)


@router.get("/callback")
async def callback(request: Request):
    c = ctx(request)
    if c.oauth is None:
        raise c.unavailable
    # Checks and uses up the state first. A member who declined, is still
    # being verified, or left the terms page comes back as a typed exception,
    # which the error handler turns into its page.
    result = await oauth.read_callback(
        c.pending, dict(request.query_params), authorize_endpoint=c.oauth.endpoints["authorize"]
    )
    user = current_user(request)
    started_by = (result.pending.data or {}).get("user_id")
    if user is None or user["id"] != started_by:
        raise oauth.STXOAuthException("invalid_state", "This sign-in was started by another session.")
    done = await c.oauth.redeem_authorization(result, store=c.tokens, member_key=str(user["id"]))
    return redirect("/dashboard", f"Connected your STX account. Allowed: {' '.join(done.scopes)}")


async def close(context: Context) -> None:
    """Nothing to close in this mode."""
