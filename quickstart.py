"""Minimal STX SDK quickstart — login + narrow selection + typed errors.

Requires stx-python installed (see README.md). Credentials read from env:

    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python quickstart.py

Compatible with stx-python >= 0.2.0a1 (PEP 8 snake_case API).
"""
from stx import STX, Selection
from stx.exceptions import STXAuthException, STXTwoFactorRequiredException


def main() -> None:
    # Region + env come from STX_REGION / STX_ENV env vars when unset here,
    # credentials from STX_EMAIL / STX_PASSWORD. See .env.example.
    with STX(region="ontario", env="staging") as client:
        try:
            client.login(params={})
        except STXTwoFactorRequiredException:
            print("2FA required — code sent to your email.")
            return
        except STXAuthException as exc:
            print(f"Login failed: {exc.message}")
            return

        # Narrow GraphQL selection — the server returns ONLY the fields you
        # ask for. This is the structural advantage over REST SDKs.
        markets = client.market_infos(
            selections=Selection("market_id", "status", "title"),
        )
        print(f"Got {len(markets)} markets. First 5:")
        for m in markets[:5]:
            # market_infos() returns List[MarketInfo] — Pydantic models,
            # not dicts. Use attribute access. Call m.model_dump() if
            # you genuinely need a plain dict back.
            print(f"  {m.market_id}: [{m.status}] {m.title}")


if __name__ == "__main__":
    main()
