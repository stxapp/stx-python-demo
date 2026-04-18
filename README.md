# stx-python-demo

Public cookbook + getting-started examples for the [STX Python SDK](https://github.com/betstackai/pysdk).

Each script here runs end-to-end against a real STX environment and is covered by CI.

## Install

Once `stx-python` is published to PyPI:

```bash
pip install stx-python
```

Until then, install directly from the SDK repo:

```bash
pip install "stx-python @ git+https://github.com/betstackai/pysdk.git#subdirectory=stx-python"
```

## Quickstart

The shortest working example:

```python
# quickstart.py
from stx import STX, Selection
from stx.exceptions import STXAuthException

client = STX(region="ontario", env="staging",
             email="you@example.com", password="...")

try:
    client.login(params={})
except STXAuthException as exc:
    print(f"Login failed: {exc.message}")
    raise

# Narrow selection — only ask for the fields you need.
markets = client.marketInfos(selections=Selection("marketId", "status", "title"))
for m in markets[:5]:
    print(f"{m['marketId']}: [{m['status']}] {m['title']}")

client.close()
```

Run it with credentials from env vars:

```bash
export STX_EMAIL="you@example.com"
export STX_PASSWORD="..."
python quickstart.py
```

See [`quickstart.py`](./quickstart.py) in the repo for the runnable version.

## Recipes

Runnable scripts that demonstrate single features end-to-end. Each pins the SDK version it was tested against.

| Script | What it shows |
|---|---|
| [`quickstart.py`](./quickstart.py) | Minimal login + narrow-selection query, exception-based error handling. |
| [`list_markets.py`](./list_markets.py) | Fetch all markets with richer selection, show the GraphQL response-shaping advantage. |

More recipes arrive as the SDK gains features:

- `market_maker_template.py` — blocked on WebSocket client ([SX-10679](https://sportsx.atlassian.net/browse/SX-10679)).
- `stream_orderbook.py` — blocked on WebSocket client.
- `reconnect_safe_ws.py` — blocked on WebSocket client.
- `export_fills_csv.py` — portfolio export, arrives alongside the retry policy ([SX-10685](https://sportsx.atlassian.net/browse/SX-10685)).

## Configuration

Every script reads credentials from the environment so you can keep them out of source:

| Variable | Purpose |
|---|---|
| `STX_EMAIL` | Your STX account email. |
| `STX_PASSWORD` | Your STX account password. |
| `STX_REGION` | `ontario` or `us`. Defaults per-script. |
| `STX_ENV` | `production` / `staging` / `demo` / `dev` / `qa`. Defaults per-script. |

Copy `.env.example` to `.env` (gitignored) and fill in values for repeated use.

## Continuous integration

GitHub Actions runs every example end-to-end against Ontario staging on every push to `main` — see [`.github/workflows/smoke.yml`](./.github/workflows/smoke.yml). Failures mean either the SDK or the API contract drifted.

Credentials used by CI live as repository secrets; no real credentials ever hit the repo.

## Contributing a recipe

1. Write a self-contained script under the repo root or `recipes/`.
2. Read credentials from env vars — never hardcode.
3. Pin the SDK version at the top (`# stx-python>=X.Y.Z`).
4. Add a row to the table above.
5. Extend `.github/workflows/smoke.yml` to run it in CI.

## License

MIT. See [LICENSE](./LICENSE).

## Related

- SDK source: [betstackai/pysdk](https://github.com/betstackai/pysdk)
- Developer docs (Mintlify, coming via [SX-10710](https://sportsx.atlassian.net/browse/SX-10710)): `docs.stxapp.com` _(planned)_
