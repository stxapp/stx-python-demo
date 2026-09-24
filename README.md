# stx-python-demo

Runnable Python examples for the **STX Python SDK** (`stx-python`, imported as `stx`). Each script is a small, self-contained workflow, such as checking who your API key belongs to, browsing markets, placing a safe order or streaming live updates, that you can copy as the starting point for your own bot or research code.

## Prerequisites

- Python 3.9 or newer
- An STX account on the environment you plan to target, and an API key for it. The scripts default to the US demo environment at `demo.stxapp.io`, which uses no real money; register there to get started.

## Install

```bash
git clone https://github.com/stxapp/stx-python-demo.git
cd stx-python-demo

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

The SDK itself installs with `pip install stx-python`, and [`requirements.txt`](./requirements.txt) pins `stx-python>=0.6.0`, the first release with API-key support. That release is not on PyPI yet, so until it lands the `pip install -r requirements.txt` line above cannot resolve; install the SDK from a built wheel instead and skip that line. Once 0.6.0 is published, the plain `pip install -r requirements.txt` is all you need.

```bash
pip install /path/to/stx_python-<version>-py3-none-any.whl
```

## 60-second quickstart

Create an API key under **Account, API Keys** in the STX app. You get a key id and an Ed25519 private key; save the key to a file such as `~/.stx/us-demo.pem`.

```bash
cp .env.example .env      # then fill in STX_KEY_ID and STX_PRIVATE_KEY
python quickstart.py
```

The scripts load `.env` automatically. If you prefer, export the variables in your shell instead:

```bash
export STX_KEY_ID="your-key-id"
export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
python quickstart.py
```

There is no login call: every request, and the WebSocket handshake, is signed with the key. When the credentials are missing, every script prints a short explanation and exits instead of a traceback.

## Examples

### Getting started

| Script | What it shows |
|---|---|
| [`quickstart.py`](./quickstart.py) | Smallest possible example: `me()` to confirm the key, then a few open markets. |
| [`identity.py`](./identity.py) | What `me()` tells you (user id, account id, scope, method) and the two errors an API key can hit. |

### Read-only data

| Script | What it shows |
|---|---|
| [`list_markets.py`](./list_markets.py) | Top-N most-active OPEN markets in a table, the view you open to find something to trade. |
| [`account_overview.py`](./account_overview.py) | Identity, deposits and withdrawals, loyalty activity, per-market position stats. |
| [`history_pulls.py`](./history_pulls.py) | Paginated `orders`, `trades` and `settlements` using `Page[T]`. |

### Trading

| Script | What it shows |
|---|---|
| [`safe_order_round_trip.py`](./safe_order_round_trip.py) | Check the key's scope, place a 1 cent LIMIT BUY that never fills, confirm it appears in history, cancel it. Cleans up in a `finally` block. |

### WebSocket streaming: markets channel

The broadcast `markets` channel supports server-side filtering on `fields`, `rule_filters` and `message_types`, plus dynamic re-selection after joining. Each script listens for about 20 seconds and focuses on one capability.

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

Per-user channels are keyed on your user id. Under API-key authentication there is no login response to read it from, so each of these scripts calls `client.me()` once before joining; that seeds the id for every client in the process.

| Script | What it shows |
|---|---|
| [`ws_personal_stream.py`](./ws_personal_stream.py) | Subscribe to the per-user `PORTFOLIO` and `ORDERS` channels (scoped to your account automatically). |
| [`ws_trades_stream.py`](./ws_trades_stream.py) | Subscribe to `TRADES`: your fills as they land, instead of polling `trades()`. |
| [`ws_settlements_stream.py`](./ws_settlements_stream.py) | Subscribe to `SETTLEMENTS`: a frame each time one of your positions resolves. |

### Long-running

| Script | What it shows |
|---|---|
| [`worker.py`](./worker.py) | The bot skeleton: one socket, `MARKETS` (bids and offers) plus your own `ORDERS`, printing events until Ctrl-C. `--seconds N` bounds the run. |

### Async patterns

| Script | What it shows |
|---|---|
| [`async_parallel_pulls.py`](./async_parallel_pulls.py) | `AsyncSTX` with `asyncio.gather` over independent calls, timing serial against parallel. |
| [`async_with_ws.py`](./async_with_ws.py) | Event-driven bot pattern: the WebSocket pushes events, `AsyncSTX` reacts over HTTP. |

All scripts build their client through [`demo_config.py`](./demo_config.py), which reads the configuration below, loads `.env`, and checks for credentials. Copy it alongside any script you take out of this repo.

## Configuration

| Variable | Purpose |
|---|---|
| `STX_KEY_ID` | Your API key id. |
| `STX_PRIVATE_KEY` | Path to the key's Ed25519 PEM file, or the PEM text itself. |
| `STX_PROFILE` | Optional. A profile name in `~/.stx/credentials` to read the key from instead of the two variables above. |
| `STX_REGION` | `us` or `ontario`. Default: `us`. |
| `STX_ENV` | `demo` or `production`. Default: `demo`. |
| `STX_HOST` | Optional. A hostname that overrides `STX_REGION` and `STX_ENV` entirely. |
| `STX_MARKET_ID` | Optional. Pins `ws_markets_order_book.py` to one market. |

The SDK reads these variables itself, with explicit constructor arguments taking precedence over the environment and the environment over a profile in `~/.stx/credentials`. The scripts pass no hardcoded region or environment, so the variables are honoured. Accounts and API keys do not carry across exchanges: a key issued for the US demo does not authenticate against the Ontario one.

An API key is issued as `read_only` or `read_write`. Market data and history work with either; placing or cancelling orders needs `read_write`. `identity.py` shows which one you hold.

The demo environments use no real money. `production` is live money; point a script there only after you have read what it does.

## Continuous integration

Two workflows run on every pull request:

- [`lint.yml`](./.github/workflows/lint.yml) runs `ruff` and byte-compiles every script. It needs no credentials.
- [`smoke.yml`](./.github/workflows/smoke.yml) runs every example end to end against the US demo environment using repository secrets (`STX_KEY_ID` and `STX_PRIVATE_KEY`, the latter holding the PEM text). A failure there means the SDK or the API contract drifted.

No credentials are stored in the repo.

## Contributing

Bug reports and small improvements are welcome via pull request; see [CONTRIBUTING.md](./CONTRIBUTING.md). To add a script: write it at the repo root, build the client through `demo_config`, add a row to the table above, and add a step to `smoke.yml`.

## Docs

Full SDK documentation: [docs.stxapp.io/sdks/python](https://docs.stxapp.io/sdks/python/). Start with the quickstart, then the authentication, trading and WebSocket guides.

## License

MIT. See [LICENSE](./LICENSE).
