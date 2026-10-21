"""Settings, read once from environment variables (see .env.example)."""

import os
from dataclasses import dataclass, field
from typing import Optional

# What the app asks members for. Every scope is described at
# https://docs.stxapp.io/oauth/scopes/
DEFAULT_MEMBER_SCOPES = "profile.read balance.read portfolio.read orders.read orders.write"

# What the app's own token asks for: the market catalog and market channels.
APP_SCOPE = "market_data"

LOGIN_MODES = ("stx", "own")


@dataclass(frozen=True)
class Settings:
    client_id: str
    client_secret: str
    redirect_uri: str
    login_mode: str = "own"
    region: str = "us"
    env: str = "demo"
    host: Optional[str] = None
    member_scopes: list[str] = field(default_factory=lambda: DEFAULT_MEMBER_SCOPES.split())
    session_secret: str = "change-me"
    token_encryption_key: Optional[str] = None
    database: str = "sample-app.db"

    @property
    def public_url(self) -> str:
        """This app's own origin, taken from the redirect URI."""
        scheme, _, rest = self.redirect_uri.partition("://")
        return f"{scheme}://{rest.split('/', 1)[0]}"


def load_settings() -> Settings:
    mode = os.environ.get("LOGIN_MODE", "own").strip().lower()
    if mode not in LOGIN_MODES:
        raise SystemExit(f"LOGIN_MODE must be one of {', '.join(LOGIN_MODES)}, not {mode!r}.")
    return Settings(
        client_id=os.environ.get("STX_OAUTH_CLIENT_ID", ""),
        client_secret=os.environ.get("STX_OAUTH_CLIENT_SECRET", ""),
        redirect_uri=os.environ.get("STX_OAUTH_REDIRECT_URI", "http://localhost:8765/callback"),
        login_mode=mode,
        region=os.environ.get("STX_REGION", "us"),
        env=os.environ.get("STX_ENV", "demo"),
        host=os.environ.get("STX_HOST") or None,
        member_scopes=os.environ.get("MEMBER_SCOPES", DEFAULT_MEMBER_SCOPES).split(),
        session_secret=os.environ.get("SESSION_SECRET", "change-me"),
        token_encryption_key=os.environ.get("TOKEN_ENCRYPTION_KEY") or None,
        database=os.environ.get("DATABASE", "sample-app.db"),
    )
