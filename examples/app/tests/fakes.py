"""Stand-ins for the exchange, so the tests make no network calls.

``FakeOAuth`` is the real ``AsyncOAuthClient`` on a mock HTTP transport: the
SDK's own state, PKCE, token storage and revoke code runs, and the token and
revoke endpoints answer from here. Its member and app clients are fakes that
return canned data or raise the error a test sets.
"""

import json
from types import SimpleNamespace
from typing import Any, Optional
from urllib.parse import parse_qs

import httpx
from stx import oauth

EXCHANGE = "https://exchange.test"


def page(items: list[Any]) -> SimpleNamespace:
    return SimpleNamespace(items=items)


class FakeMember:
    """The parts of ``AsyncSTX`` the app calls for a member."""

    def __init__(self, owner: "FakeOAuth", member_key: str) -> None:
        self.owner = owner
        self.member_key = member_key

    async def __aenter__(self) -> "FakeMember":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        pass

    async def close(self) -> None:
        pass

    def _maybe_raise(self, name: str) -> None:
        exc = self.owner.raises.get(name)
        if exc is not None:
            raise exc

    async def balance(self):
        self._maybe_raise("balance")
        return SimpleNamespace(available_balance="1234.5000", account_balance="1300.0000")

    async def positions(self):
        self._maybe_raise("positions")
        return [
            SimpleNamespace(market_id="m1", position="2.00", premium="0.80", open_risk="0.80"),
            SimpleNamespace(market_id="m2", position="0.00", premium="0", open_risk="0"),
        ]

    async def orders(self, **query):
        self._maybe_raise("orders")
        self.owner.calls.append(("orders", query))
        return page(
            [
                SimpleNamespace(
                    id="o1", market_id="m1", action="buy", price="0.4000", quantity="1.00", filled="0.00", status="open"
                )
            ]
        )

    async def fills(self, **query):
        self._maybe_raise("fills")
        return page([])

    async def settlements(self, **query):
        self._maybe_raise("settlements")
        return page([])

    async def place_order(self, market_id, action, order_type, **kwargs):
        self._maybe_raise("place_order")
        self.owner.calls.append(("place_order", (market_id, action, order_type), kwargs))
        return SimpleNamespace(id="o2", status="accepted")

    async def cancel_order(self, order_id):
        self._maybe_raise("cancel_order")
        self.owner.calls.append(("cancel_order", order_id))
        return SimpleNamespace(order_id=order_id, status="cancelled")


class FakeCatalog:
    """The app client: ``markets()`` and ``market()``."""

    def __init__(self) -> None:
        self.market_one = SimpleNamespace(
            market_id="m1",
            symbol="STXTEST-M1",
            title="Will the home team win?",
            event_title="Away at Home",
            event_short_title="AWY @ HOM",
            sport="Football",
            bids=[SimpleNamespace(price="0.4000", quantity="10.00")],
            offers=[SimpleNamespace(price="0.6000", quantity="5.00")],
            last_traded_price="0.5000",
            max_price="1.0000",
        )

    async def markets(self, **query):
        return page([self.market_one])

    async def market(self, market_id):
        return self.market_one

    async def close(self) -> None:
        pass


class FakeOAuth(oauth.AsyncOAuthClient):
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.raises: dict[str, Exception] = {}
        self.calls: list[Any] = []
        super().__init__(
            client_id="stxapp_client_test",
            client_secret="stxapp_secret_test",
            redirect_uri="http://localhost:8765/callback",
            scope="profile.read balance.read orders.read orders.write",
            host=EXCHANGE,
            transport=httpx.MockTransport(self._handle),
        )

    def _handle(self, request: httpx.Request) -> httpx.Response:
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        self.requests.append({"path": request.url.path, "form": form})
        if request.url.path == "/oauth/token" and form.get("grant_type") == "authorization_code":
            body = {
                "access_token": "stxapp_at_test",
                "refresh_token": "stxapp_rt_test",
                "token_type": "bearer",
                "expires_in": 3600,
                "scope": "profile.read balance.read orders.read orders.write",
            }
            return httpx.Response(200, content=json.dumps(body), headers={"content-type": "application/json"})
        if request.url.path == "/oauth/revoke":
            return httpx.Response(200)
        return httpx.Response(400, json={"error": "invalid_request"})

    def member_client(self, store: Any, member_key: str, **kwargs: Any) -> FakeMember:
        return FakeMember(self, member_key)

    def app_client(self, scope: Any = None, **kwargs: Any) -> FakeCatalog:
        return FakeCatalog()


class FakeConnect:
    """``AsyncConnect`` for LOGIN_MODE=stx: start() and finish()."""

    def __init__(self, sub: str = "stx-sub-1", email: Optional[str] = "member@example.com") -> None:
        self.sub = sub
        self.email = email
        self.finish_raises: Optional[Exception] = None
        self.started = 0

    async def start(self, **kwargs: Any) -> oauth.StartedSignIn:
        self.started += 1
        state = f"state-{self.started}"
        return oauth.StartedSignIn(
            state=state,
            code_verifier="verifier",
            nonce="nonce",
            redirect_uri="http://localhost:8765/callback",
            url=f"{EXCHANGE}/oauth/authorize?state={state}",
        )

    async def finish(self, callback: dict[str, str], saved: oauth.SavedSignIn) -> oauth.FinishedSignIn:
        if callback.get("state") != saved.state:
            raise oauth.STXOAuthException("invalid_state", "state mismatch")
        if self.finish_raises is not None:
            raise self.finish_raises
        tokens = oauth.TokenSet(access_token="stxapp_at_x", refresh_token="stxapp_rt_x", scope="openid balance.read")
        return oauth.FinishedSignIn(tokens, oauth.ConnectIdentity(sub=self.sub, email=self.email))

    async def close(self) -> None:
        pass
