import base64
import os
import tempfile
import time
import unittest

import stx
from cryptography.exceptions import InvalidTag
from stx import oauth

from sample.errors import describe
from sample.store import Database, PendingStore, TokenCipher, TokenStore

KEY = base64.b64encode(os.urandom(32)).decode()


def database(key=KEY):
    path = os.path.join(tempfile.mkdtemp(), "test.db")
    return Database(path, TokenCipher(key))


class TokenCipherTest(unittest.TestCase):
    def test_round_trip_and_no_plaintext(self):
        cipher = TokenCipher(KEY)
        sealed = cipher.seal("stxapp_rt_secret")
        self.assertTrue(sealed.startswith("enc:v1:"))
        self.assertNotIn("stxapp_rt_secret", sealed)
        self.assertEqual(cipher.open(sealed), "stxapp_rt_secret")

    def test_each_seal_is_different(self):
        cipher = TokenCipher(KEY)
        self.assertNotEqual(cipher.seal("x"), cipher.seal("x"))

    def test_without_a_key_values_pass_through(self):
        cipher = TokenCipher(None)
        self.assertFalse(cipher.enabled)
        self.assertEqual(cipher.seal("plain"), "plain")
        self.assertEqual(cipher.open("plain"), "plain")

    def test_an_encrypted_value_needs_the_key(self):
        sealed = TokenCipher(KEY).seal("x")
        with self.assertRaises(ValueError):
            TokenCipher(None).open(sealed)
        with self.assertRaises(InvalidTag):
            TokenCipher(base64.b64encode(os.urandom(32)).decode()).open(sealed)

    def test_a_key_must_be_32_bytes(self):
        with self.assertRaises(ValueError):
            TokenCipher(base64.b64encode(b"short").decode())


class StoresTest(unittest.TestCase):
    def test_token_store_keeps_tokens_encrypted(self):
        db = database()
        store = TokenStore(db)
        self.assertIsNone(store.get("1"))
        store.set("1", oauth.StoredTokens(access_token="stxapp_at_a", refresh_token="stxapp_rt_a", expires_at=10.0))
        self.assertEqual(store.get("1").refresh_token, "stxapp_rt_a")
        raw = db.execute("select tokens from stx_tokens").fetchone()["tokens"]
        self.assertNotIn("stxapp_", raw)
        store.set("1", oauth.StoredTokens(access_token="stxapp_at_b", refresh_token="stxapp_rt_b"))
        self.assertEqual(store.get("1").access_token, "stxapp_at_b")
        store.delete("1")
        self.assertIsNone(store.get("1"))

    def test_a_pending_sign_in_is_used_once(self):
        store = PendingStore(database())
        store.put("s1", oauth.PendingAuthorization(code_verifier="v", redirect_uri="r", data={"user_id": 1}))
        self.assertEqual(store.take("s1").data, {"user_id": 1})
        self.assertIsNone(store.take("s1"))

    def test_an_expired_pending_sign_in_is_gone(self):
        store = PendingStore(database())
        store.put("s1", oauth.PendingAuthorization(code_verifier="v", redirect_uri="r", expires_at=time.time() - 1))
        self.assertIsNone(store.take("s1"))


class DescribeTest(unittest.TestCase):
    def page(self, exc):
        return describe(exc, connect_url="/connect", return_url="https://app.test/dashboard")

    def test_grant_revoked_offers_to_connect_again(self):
        p = self.page(oauth.STXGrantRevokedException())
        self.assertEqual((p.status, p.code, p.action_url), (401, "grant_revoked", "/connect"))

    def test_terms_required_links_to_the_stx_terms_page_with_a_return_address(self):
        exc = stx.STXTermsRequiredException(
            "terms", terms_url="https://demo.stxapp.io/connect/terms?client_id=c1", status_code=403
        )
        p = self.page(exc)
        self.assertEqual((p.status, p.code), (403, "terms_required"))
        self.assertTrue(p.action_url.startswith("https://demo.stxapp.io/connect/terms?client_id=c1&return_to="))
        self.assertIn("return_to=https%3A%2F%2Fapp.test%2Fdashboard", p.action_url)

    def test_callback_errors(self):
        cases = {
            oauth.STXAccountPendingException("account_pending"): "account_pending",
            oauth.STXTermsNotAcceptedException("terms_required"): "terms_required",
            oauth.STXAccessDeniedException("access_denied"): "access_denied",
            oauth.STXOAuthException("invalid_state", "used"): "invalid_state",
        }
        for exc, code in cases.items():
            with self.subTest(code=code):
                self.assertEqual(self.page(exc).code, code)

    def test_account_pending_links_to_the_docs(self):
        p = self.page(oauth.STXAccountPendingException("account_pending"))
        self.assertIn("members-being-verified", p.action_url)

    def test_ip_not_allowed(self):
        p = self.page(stx.STXIpNotAllowedException("ip_not_allowed", status_code=403))
        self.assertEqual((p.status, p.code), (403, "ip_not_allowed"))
        self.assertIn("ip-allow-list", p.action_url)

    def test_insufficient_scope_names_the_scope(self):
        p = self.page(stx.STXInsufficientScopeException("scope", required_scopes=["orders.write"], status_code=403))
        self.assertEqual(p.code, "insufficient_scope")
        self.assertIn("orders.write", p.message)

    def test_a_rejected_order_shows_stx_reason(self):
        p = self.page(stx.STXRejectedException("Market does not accept orders.", status_code=422))
        self.assertEqual((p.status, p.code), (422, "rejected"))
        self.assertIn("Market does not accept orders.", p.message)

    def test_not_available_names_the_feature_and_host(self):
        p = self.page(stx.STXNotAvailableError("oauth", host="demo.stxapp.ca"))
        self.assertEqual((p.status, p.code), (501, "not_available"))
        self.assertIn("demo.stxapp.ca", p.message)
        self.assertIn("'oauth'", p.message)


if __name__ == "__main__":
    unittest.main()
