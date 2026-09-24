# stx-python-demo

Runnable Python examples for the **STX Python SDK** (`stx-python`, imported as `stx`). Each script is a small, self-contained workflow, such as logging in, browsing markets, placing a safe order or streaming live updates, that you can copy as the starting point for your own bot or research code.

## Prerequisites

- Python 3.9 or newer
- An STX account on the environment you plan to target. The scripts default to the US demo environment at `demo.stxapp.io`, which uses no real money; register there to get started.

## Install

```bash
git clone https://github.com/stxapp/stx-python-demo.git
cd stx-python-demo

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

The SDK itself installs with `pip install stx-python`. Until its first release on PyPI it is published to TestPyPI as a pre-release, so [`requirements.txt`](./requirements.txt) carries the index lines that point pip at TestPyPI for this one package. Once the SDK is on PyPI that file becomes a single `stx-python` line and the plain `pip install` is all you need.

## 60-second quickstart

```bash
cp .env.example .env      # then fill in STX_EMAIL and STX_PASSWORD
python quickstart.py
```

The scripts load `.env` automatically. If you prefer, export the variables in your shell instead:

```bash
export STX_EMAIL="you@example.com"
export STX_PASSWORD="your-password"
python quickstart.py
```

When the credentials are missing, every script prints a short explanation and exits instead of a traceback.

## Examples

### Getting started

| Script | What it shows |
|---|---|
| [`quickstart.py`](./quickstart.py) | Smallest possible example: log in and pull a few open markets. |
| [`auth_flow.py`](./auth_flow.py) | The three branches a production caller handles: plain login, the 2FA challenge, and automatic token refresh. |

### Read-only data

| Script | What it shows |
|---|---|
| [`list_markets.py`](./list_markets.py) | Top-N most-active OPEN markets in a table, the view you open to find something to trade. |
| [`account_overview.py`](./account_overview.py) | Balances, loyalty tier, per-market position stats. |
| [`history_pulls.py`](./history_pulls.py) | Paginated `orders`, `trades` and `settlements` using `Page[T]`. |

### Trading

| Script | What it shows |
|---|---|
| [`safe_order_round_trip.py`](./safe_order_round_trip.py) | Place a 1 cent LIMIT BUY that never fills, confirm it appears in history, cancel it. Cleans up in a `finally` block. |

### WebSocket streaming: markets channel

The broadcast `markets` channel supports server-side filtering on `fields`, `rule_filters` and `message_types`, plus dynamic re-selection after joining. Each script listens for about 30 seconds and focuses on one capability.

| Script | What it shows |
|---|---|
| [`ws_markets_basic.py`](./ws_markets_basic.py) | Default join: every field, every rule, both message types. |
| [`ws_markets_bids_offers.py`](./ws_markets_bids_offers.py) | Narrow `fields` to `["bids", "offers"]` for a liquidity-only feed. |
| [`ws_markets_rule_filters.py`](./ws_markets_rule_filters.py) | Server-side filter to specific market rule types (for example `spread`, `home_winner`). |
| [`ws_markets_message_types.py`](./ws_markets_message_types.py) | Receive only `market_updated` events and skip `market_created`. |
| [`ws_markets_dynamic.py`](./ws_markets_dynamic.py) | Change filters mid-stream with `ws.push(...)`: `select_fields`, `select_rule_filters`. |
| [`ws_markets_order_book.py`](./ws_markets_order_book.py) | Pin to one market and render its top of book. Discovers an OPEN market if `STX_MARKET_ID` is unset. |
| [`ws_markets_multi_order_book.py`](./ws_markets_multi_order_book.py) | Maintain a dict of order books for every market matching a rule filter. |

### WebSocket streaming: your account

| Script | What it shows |
|---|---|
| [`ws_personal_stream.py`](./ws_personal_stream.py) | Subscribe to the per-user `PORTFOLIO` and `ORDERS` channels (scoped to your account automatically). |

### Async patterns

| Script | What it shows |
|---|---|
| [`async_parallel_pulls.py`](./async_parallel_pulls.py) | `AsyncSTX` with `asyncio.gather` over independent calls, timing serial against parallel. |
| [`async_with_ws.py`](./async_with_ws.py) | Event-driven bot pattern: the WebSocket pushes events, `AsyncSTX` reacts over HTTP. |

All scripts build their client through [`demo_config.py`](./demo_config.py), which reads the configuration below, loads `.env`, and checks for credentials. Copy it alongside any script you take out of this repo.

## Configuration

| Variable | Purpose |
|---|---|
| `STX_EMAIL` | Your STX account email. |
| `STX_PASSWORD` | Your STX account password. |
| `STX_REGION` | `us` or `ontario`. Default: `us`. |
| `STX_ENV` | `demo` or `production`. Default: `demo`. |
| `STX_HOST` | Optional. A hostname that overrides `STX_REGION` and `STX_ENV` entirely. |
| `STX_MARKET_ID` | Optional. Pins `ws_markets_order_book.py` to one market. |

The SDK reads these variables itself, with explicit constructor arguments taking precedence over the environment and the environment over a profile in `~/.stx/credentials`. The scripts pass no hardcoded region or environment, so the variables are honoured. Accounts do not carry across exchanges: an account registered on the US demo does not log in to the Ontario one.

The demo environments use no real money. `production` is live money; point a script there only after you have read what it does.

## Continuous integration

Two workflows run on every pull request:

- [`lint.yml`](./.github/workflows/lint.yml) runs `ruff` and byte-compiles every script. It needs no credentials.
- [`smoke.yml`](./.github/workflows/smoke.yml) runs every example end to end against a live environment using repository secrets. A failure there means the SDK or the API contract drifted.

No credentials are stored in the repo.

## Contributing

Bug reports and small improvements are welcome via pull request; see [CONTRIBUTING.md](./CONTRIBUTING.md). To add a script: write it at the repo root, build the client through `demo_config`, add a row to the table above, and add a step to `smoke.yml`.

## Docs

Full SDK documentation: [docs.stxapp.io/sdks/python](https://docs.stxapp.io/sdks/python/). Start with the quickstart, then the authentication, trading and WebSocket guides.

## License

MIT. See [LICENSE](./LICENSE).
