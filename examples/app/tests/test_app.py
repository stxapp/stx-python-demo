import asyncio
import os
import re
import tempfile
import unittest
from unittest import mock

import anyio
import stx
from fastapi.testclient import TestClient
from stx import oauth

from sample import live, main
from sample.config import Settings
from tests.fakes import EXCHANGE, FakeConnect, FakeOAuth


def settings(mode: str) -> Settings:
    return Settings(
        client_id="stxapp_client_test",
        client_secret="stxapp_secret_test",
        redirect_uri="https://app.test/callback",
        login_mode=mode,
        session_secret="test",
        database=os.path.join(tempfile.mkdtemp(), "test.db"),
    )


def error_code(res) -> str:
    m = re.search(r'data-code="([^"]*)"', res.text)
    return m.group(1) if m else ""


class OwnModeTest(unittest.TestCase):
    """LOGIN_MODE=own: the app's own login, then connect an STX account."""

    def setUp(self):
        self.oauth = FakeOAuth()
        self.app = main.create_app(settings("own"), oauth_client=self.oauth)
        self.client = TestClient(self.app, follow_redirects=False).__enter__()
        self.ctx = self.app.state.ctx

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def sign_in(self, name="alice"):
        res = self.client.post("/login", data={"name": name})
        self.assertEqual(res.status_code, 303)

    def connect(self):
        res = self.client.get("/connect")
        self.assertEqual(res.status_code, 303)
        state = re.search(r"state=([^&]+)", res.headers["location"]).group(1)
        return self.client.get(f"/callback?code=stxapp_code_1&state={state}")

    def test_health_and_public_pages(self):
        self.assertEqual(self.client.get("/healthz").json()["oauth"], True)
        self.assertEqual(self.client.get("/").status_code, 200)
        res = self.client.get("/markets")
        self.assertEqual(res.status_code, 200)
        self.assertIn("AWY @ HOM", res.text)
        self.assertEqual(self.client.get("/markets/m1").status_code, 200)

    def test_connect_sends_the_member_to_stx_with_pkce(self):
        self.sign_in()
        res = self.client.get("/connect")
        self.assertEqual(res.status_code, 303)
        url = res.headers["location"]
        self.assertTrue(url.startswith(f"{EXCHANGE}/oauth/authorize?"))
        self.assertIn("code_challenge_method=S256", url)

    def test_connect_needs_a_signed_in_user(self):
        self.assertEqual(self.client.get("/connect").headers["location"], "/login")

    def test_callback_stores_the_tokens_under_our_user_id(self):
        self.sign_in()
        res = self.connect()
        self.assertEqual(res.status_code, 303)
        self.assertTrue(res.headers["location"].startswith("/dashboard?msg="))
        user_id = str(self.client.app.state.ctx.db.user_by_name("alice")["id"])
        self.assertEqual(self.ctx.tokens.get(user_id).refresh_token, "stxapp_rt_test")
        exchange = [r for r in self.oauth.requests if r["path"] == "/oauth/token"][0]["form"]
        self.assertEqual(exchange["grant_type"], "authorization_code")
        self.assertIn("code_verifier", exchange)

    def test_a_replayed_callback_is_refused(self):
        self.sign_in()
        res = self.client.get("/connect")
        state = re.search(r"state=([^&]+)", res.headers["location"]).group(1)
        self.client.get(f"/callback?code=c&state={state}")
        again = self.client.get(f"/callback?code=c&state={state}")
        self.assertEqual((again.status_code, error_code(again)), (400, "invalid_state"))

    def test_a_callback_for_another_users_sign_in_is_refused(self):
        self.sign_in("alice")
        res = self.client.get("/connect")
        state = re.search(r"state=([^&]+)", res.headers["location"]).group(1)
        self.sign_in("mallory")
        res = self.client.get(f"/callback?code=c&state={state}")
        self.assertEqual(error_code(res), "invalid_state")
        self.assertFalse([r for r in self.oauth.requests if r["path"] == "/oauth/token"])

    def test_callback_errors_show_their_pages(self):
        for error, code in [
            ("terms_required", "terms_required"),
            ("account_pending", "account_pending"),
            ("access_denied", "access_denied"),
        ]:
            with self.subTest(error=error):
                self.sign_in()
                res = self.client.get("/connect")
                state = re.search(r"state=([^&]+)", res.headers["location"]).group(1)
                res = self.client.get(f"/callback?error={error}&state={state}")
                self.assertEqual(res.status_code, 403)
                self.assertEqual(error_code(res), code)

    def test_dashboard_before_connecting_offers_to_connect(self):
        self.sign_in()
        res = self.client.get("/dashboard")
        self.assertIn("Connect your STX account", res.text)
        self.assertIn('href="/connect"', res.text)

    def test_dashboard_shows_the_account_and_hides_flat_positions(self):
        self.sign_in()
        self.connect()
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn("1234.5000", res.text)
        self.assertIn("2.00", res.text)
        self.assertNotIn("<td>0.00</td><td>0</td>", res.text)
        self.assertIn(("orders", {"status": "open", "limit": 25}), self.oauth.calls)

    def test_a_section_without_its_scope_says_so(self):
        self.sign_in()
        self.connect()
        self.oauth.raises["positions"] = stx.STXInsufficientScopeException(
            "scope", required_scopes=["portfolio.read"], status_code=403
        )
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Needs portfolio.read.", res.text)

    def test_place_and_cancel_an_order(self):
        self.sign_in()
        self.connect()
        res = self.client.post("/orders", data={"market_id": "m1", "action": "buy", "price": "0.01", "quantity": "1"})
        self.assertEqual(res.status_code, 303)
        self.assertIn("o2", res.headers["location"])
        name, args, kwargs = self.oauth.calls[-1]
        self.assertEqual((name, args), ("place_order", ("m1", "buy", "limit")))
        self.assertEqual((kwargs["price"], kwargs["quantity"]), ("0.01", "1"))
        self.assertTrue(kwargs["client_order_id"].startswith("sample-"))
        res = self.client.post("/orders/o2/cancel")
        self.assertEqual(res.status_code, 303)
        self.assertEqual(self.oauth.calls[-1], ("cancel_order", "o2"))

    def test_orders_need_a_connection(self):
        self.sign_in()
        res = self.client.post("/orders", data={"market_id": "m1", "action": "buy", "price": "0.01", "quantity": "1"})
        self.assertEqual(res.headers["location"], "/dashboard")

    def test_refused_orders_show_their_pages(self):
        self.sign_in()
        self.connect()
        cases = [
            (oauth.STXGrantRevokedException(), 401, "grant_revoked"),
            (stx.STXIpNotAllowedException("ip", status_code=403), 403, "ip_not_allowed"),
            (
                stx.STXTermsRequiredException(
                    "terms", terms_url="https://exchange.test/connect/terms?client_id=c", status_code=403
                ),
                403,
                "terms_required",
            ),
        ]
        for exc, status, code in cases:
            with self.subTest(code=code):
                self.oauth.raises["place_order"] = exc
                res = self.client.post(
                    "/orders", data={"market_id": "m1", "action": "buy", "price": "0.01", "quantity": "1"}
                )
                self.assertEqual((res.status_code, error_code(res)), (status, code))
        self.assertIn("return_to=https%3A%2F%2Fapp.test%2Fdashboard", res.text)

    def test_unlink_revokes_at_stx_and_deletes_the_tokens(self):
        self.sign_in()
        self.connect()
        res = self.client.post("/unlink")
        self.assertEqual(res.status_code, 303)
        revoke = [r for r in self.oauth.requests if r["path"] == "/oauth/revoke"]
        self.assertEqual(revoke[0]["form"]["token"], "stxapp_rt_test")
        user_id = str(self.ctx.db.user_by_name("alice")["id"])
        self.assertIsNone(self.ctx.tokens.get(user_id))

    def test_sign_out_keeps_the_connection(self):
        self.sign_in()
        self.connect()
        self.client.post("/logout")
        user_id = str(self.ctx.db.user_by_name("alice")["id"])
        self.assertIsNotNone(self.ctx.tokens.get(user_id))
        self.assertEqual(self.client.get("/dashboard").headers["location"], "/")


class StxModeTest(unittest.TestCase):
    """LOGIN_MODE=stx: sign in with an STX account, which also connects it."""

    def setUp(self):
        self.oauth = FakeOAuth()
        self.app = main.create_app(settings("stx"), oauth_client=self.oauth)
        self.client = TestClient(self.app, follow_redirects=False).__enter__()
        self.ctx = self.app.state.ctx
        self.ctx.connect = FakeConnect()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def sign_in(self):
        res = self.client.get("/login?connection=google")
        self.assertEqual(res.status_code, 303)
        state = re.search(r"state=([^&]+)", res.headers["location"]).group(1)
        return self.client.get(f"/callback?code=c&state={state}")

    def test_home_offers_sign_in_with_stx(self):
        self.assertIn("Sign in with your STX account", self.client.get("/").text)

    def test_sign_in_creates_a_user_keyed_on_the_stx_sub(self):
        res = self.sign_in()
        self.assertEqual(res.status_code, 303)
        user = self.ctx.db.user_by_sub("stx-sub-1")
        self.assertEqual(user["name"], "member@example.com")
        self.assertEqual(self.ctx.tokens.get(str(user["id"])).refresh_token, "stxapp_rt_x")
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

    def test_signing_in_again_finds_the_same_user(self):
        self.sign_in()
        self.client.post("/logout")
        self.sign_in()
        count = self.ctx.db.execute("select count(*) as n from users").fetchone()["n"]
        self.assertEqual(count, 1)

    def test_the_verifier_stays_on_the_server(self):
        self.client.get("/login")
        self.assertNotIn("verifier", self.client.cookies.get("session", ""))
        self.assertEqual(self.ctx.db.execute("select count(*) as n from pending_sign_ins").fetchone()["n"], 1)

    def test_a_callback_without_a_sign_in_in_this_browser_is_refused(self):
        res = self.client.get("/callback?code=c&state=state-1")
        self.assertEqual((res.status_code, error_code(res)), (400, "invalid_state"))

    def test_callback_errors_show_their_pages(self):
        self.ctx.connect.finish_raises = oauth.STXTermsNotAcceptedException("terms_required")
        res = self.sign_in()
        self.assertEqual(error_code(res), "terms_required")
        self.assertIn('href="/login"', res.text)

    def test_a_revoked_grant_sends_the_member_to_sign_in_again(self):
        self.sign_in()
        self.oauth.raises["balance"] = oauth.STXGrantRevokedException()
        res = self.client.get("/dashboard")
        self.assertEqual((res.status_code, error_code(res)), (401, "grant_revoked"))
        self.assertIn('href="/login"', res.text)


class NotAvailableTest(unittest.TestCase):
    def test_every_page_explains_an_exchange_without_oauth(self):
        unavailable = stx.STXNotAvailableError("oauth", host="demo.stxapp.ca")
        with mock.patch.object(main, "build_oauth", side_effect=unavailable):
            app = main.create_app(settings("stx"))
            with TestClient(app, follow_redirects=False) as client:
                self.assertEqual(client.get("/healthz").json()["oauth"], False)
                for path in ("/markets", "/login", "/dashboard"):
                    with self.subTest(path=path):
                        res = client.get(path)
                        self.assertEqual((res.status_code, error_code(res)), (501, "not_available"))
                        self.assertIn("demo.stxapp.ca", res.text)


class LiveTest(unittest.TestCase):
    def test_account_state_counts_open_positions(self):
        view = mock.Mock(
            balance={"available_balance": "10.0000", "account_balance": "12.0000"},
            open_orders=[{"id": "o1", "market_id": "m1", "action": "buy", "price": "0.4", "quantity": "1"}],
            positions=[{"position": "2.00"}, {"position": "0.00"}],
            fills=[{}, {}],
        )
        state = live.account_state(view)
        self.assertEqual(state["available_balance"], "10.0000")
        self.assertEqual(state["positions"], 1)
        self.assertEqual(state["fills"], 2)
        self.assertEqual(state["open_orders"][0]["id"], "o1")

    def test_sse_format(self):
        self.assertEqual(live.sse("book", {"a": 1}), 'event: book\ndata: {"a": 1}\n\n')

    def test_closing_finishes_even_when_the_stream_is_cancelled(self):
        class Socket:
            closed = False

            async def close(self):
                await asyncio.sleep(0.01)  # e.g. leaving each channel
                self.closed = True

        sock = Socket()

        async def stream():
            async with live.closing(sock):
                await asyncio.sleep(3600)

        async def scenario():
            # What the server does when the browser closes the page.
            async with anyio.create_task_group() as tg:
                tg.start_soon(stream)
                await asyncio.sleep(0.01)
                tg.cancel_scope.cancel()

        asyncio.run(scenario())
        self.assertTrue(sock.closed)

    def test_the_account_feed_needs_a_connection(self):
        app = main.create_app(settings("own"), oauth_client=FakeOAuth())
        with TestClient(app) as client:
            self.assertEqual(client.get("/live/account").status_code, 401)


if __name__ == "__main__":
    unittest.main()
