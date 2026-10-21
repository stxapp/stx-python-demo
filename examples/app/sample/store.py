"""The app's own data in SQLite: its users, each member's STX tokens, and
sign-ins in progress.

``TokenStore`` and ``PendingStore`` implement the two store protocols of
``stx.oauth`` (get/set/delete and put/take), so the SDK reads and writes
tokens here, including after every refresh. Tokens are encrypted at rest
when ``TOKEN_ENCRYPTION_KEY`` is set.
"""

import base64
import json
import os
import sqlite3
import threading
import time
from typing import Any, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from stx import oauth

PREFIX = "enc:v1:"


class TokenCipher:
    """AES-256-GCM for tokens at rest. With no key, values pass through as they are
    (fine on a laptop, not in production)."""

    def __init__(self, key_b64: Optional[str]) -> None:
        self._aead: Optional[AESGCM] = None
        if key_b64:
            key = base64.b64decode(key_b64)
            if len(key) != 32:
                raise ValueError("TOKEN_ENCRYPTION_KEY must be 32 bytes, base64-encoded")
            self._aead = AESGCM(key)

    @property
    def enabled(self) -> bool:
        return self._aead is not None

    def seal(self, plain: str) -> str:
        if self._aead is None:
            return plain
        nonce = os.urandom(12)
        body = self._aead.encrypt(nonce, plain.encode(), None)
        return PREFIX + base64.urlsafe_b64encode(nonce + body).decode()

    def open(self, stored: str) -> str:
        if not stored.startswith(PREFIX):
            return stored
        if self._aead is None:
            raise ValueError("A token is encrypted but TOKEN_ENCRYPTION_KEY is not set")
        raw = base64.urlsafe_b64decode(stored[len(PREFIX) :])
        return self._aead.decrypt(raw[:12], raw[12:], None).decode()


SCHEMA = """
create table if not exists users (
  id integer primary key autoincrement,
  name text not null,
  stx_sub text unique,            -- LOGIN_MODE=stx: the member's stable STX id
  created_at real not null
);
create table if not exists stx_tokens (
  user_id text primary key,       -- the member key the SDK uses
  tokens text not null,           -- StoredTokens as JSON, sealed
  updated_at real not null
);
create table if not exists pending_sign_ins (
  state text primary key,
  data text not null,
  expires_at real not null
);
"""


class Database:
    def __init__(self, path: str, cipher: TokenCipher) -> None:
        self.cipher = cipher
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def execute(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self._lock, self._conn:
            return self._conn.execute(sql, args)

    def take_pending(self, state: str) -> Optional[dict[str, Any]]:
        """Read and delete one pending sign-in in a single step, so a replayed
        callback finds nothing. Expired entries are dropped first."""
        with self._lock, self._conn:
            self._conn.execute("delete from pending_sign_ins where expires_at <= ?", (time.time(),))
            row = self._conn.execute("select data from pending_sign_ins where state = ?", (state,)).fetchone()
            self._conn.execute("delete from pending_sign_ins where state = ?", (state,))
        return json.loads(row["data"]) if row else None

    # ---- users -----------------------------------------------------------

    def create_user(self, name: str, stx_sub: Optional[str] = None) -> int:
        cur = self.execute(
            "insert into users (name, stx_sub, created_at) values (?, ?, ?)", (name, stx_sub, time.time())
        )
        return int(cur.lastrowid)

    def user(self, user_id: int) -> Optional[dict[str, Any]]:
        row = self.execute("select * from users where id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def user_by_name(self, name: str) -> Optional[dict[str, Any]]:
        row = self.execute("select * from users where name = ? and stx_sub is null", (name,)).fetchone()
        return dict(row) if row else None

    def user_by_sub(self, stx_sub: str) -> Optional[dict[str, Any]]:
        row = self.execute("select * from users where stx_sub = ?", (stx_sub,)).fetchone()
        return dict(row) if row else None


class TokenStore:
    """``stx.oauth.TokenStore`` over the stx_tokens table, keyed by our user id."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def get(self, member_key: str) -> Optional[oauth.StoredTokens]:
        row = self.db.execute("select tokens from stx_tokens where user_id = ?", (member_key,)).fetchone()
        if row is None:
            return None
        return oauth.StoredTokens.from_dict(json.loads(self.db.cipher.open(row["tokens"])))

    def set(self, member_key: str, tokens: oauth.StoredTokens) -> None:
        sealed = self.db.cipher.seal(json.dumps(tokens.to_dict()))
        self.db.execute(
            "insert into stx_tokens (user_id, tokens, updated_at) values (?, ?, ?) "
            "on conflict (user_id) do update set tokens = excluded.tokens, updated_at = excluded.updated_at",
            (member_key, sealed, time.time()),
        )

    def delete(self, member_key: str) -> None:
        self.db.execute("delete from stx_tokens where user_id = ?", (member_key,))


class PendingStore:
    """``stx.oauth.PendingAuthorizationStore`` over pending_sign_ins: each
    state is used once and expires. It also keeps the Sign in with STX
    ``SavedSignIn`` (``put_raw``/``take_raw``), so no verifier rides in a cookie."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def put_raw(self, state: str, data: dict[str, Any], expires_at: float) -> None:
        self.db.execute(
            "insert or replace into pending_sign_ins (state, data, expires_at) values (?, ?, ?)",
            (state, json.dumps(data), expires_at),
        )

    def take_raw(self, state: str) -> Optional[dict[str, Any]]:
        return self.db.take_pending(state)

    # The SDK's protocol:
    def put(self, state: str, pending: oauth.PendingAuthorization) -> None:
        self.put_raw(state, pending.to_dict(), pending.expires_at)

    def take(self, state: str) -> Optional[oauth.PendingAuthorization]:
        data = self.take_raw(state)
        return oauth.PendingAuthorization.from_dict(data) if data else None
