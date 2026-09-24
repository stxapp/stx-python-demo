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

The scripts load `.env` automatically. If you prefer, export the variables in your shell instead, or name a profile in `~/.stx/credentials` with `STX_PROFILE`:

```bash
export STX_KEY_ID="your-key-id"
export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
python quickstart.py
```

There is no login call: every request, and the WebSocket handshake, is signed with the key. When the credentials are missing, every script prints a short explanation and exits instead of a traceback.

**Amounts are strings.** Every price, balance and fee comes back as a dollar string exactly as the API sends it (`"0.5600"`), and every quantity as a contract count string (`"2.00"`). The scripts print them as they are. Orders take strings too: `place_order(market_id, "buy", "limit", price="0.01", quantity="1")`.

## Examples

### Getting started

| Script | What it shows |
|---|---|
| [`quickstart.py`](./quickstart.py) | Smallest possible example: `me()` to confirm the key, then a few open markets. |
| [`identity.py`](./identity.py) | What `me()` tells you (user id, account id, scope, method) and the two errors an API key can hit. |

### Read-only data

| Script | What it shows |
|---|---|
| [`list_markets.py`](./list_markets.py) | The most active open markets in a table, walking pages with `iter_markets`. |
| [`account_overview.py`](./account_overview.py) | Identity, balance, open positions, deposits and withdrawals, loyalty, per-market stats. |
| [`history_pulls.py`](./history_pulls.py) | Orders, fills and settlements, one `Page` at a time and across pages with the cursor. |

### Trading

| Script | What it shows |
|---|---|
| [`safe_order_round_trip.py`](./safe_order_round_trip.py) | Check the key's scope, place a 1-cent limit buy that never fills, find it by `client_order_id`, cancel it. Cleans up in a `finally` block. |
| [`batch_orders.py`](./batch_orders.py) | `place_orders` in one request (two resting buys and one the exchange rejects), then `cancel_orders` and `cancel_all_orders`. |

### WebSocket channels

One script per documented channel. Each joins, prints the join reply and the snapshot where the channel has one, then prints what arrives for `--seconds` (default 20). The demo exchange can be quiet, so an empty listen window is normal.

| Script | Channel | What it shows |
|---|---|---|
| [`ws_orderbook.py`](./ws_orderbook.py) | `orderbook` | Full book per market on every push; `select_market_ids` to change markets. |
| [`ws_ticker.py`](./ws_ticker.py) | `ticker` | Price, top of book and volume whenever a market moves. |
| [`ws_trades.py`](./ws_trades.py) | `trades` | Every execution on the exchange, anonymised, with the taker's side. |
| [`ws_markets.py`](./ws_markets.py) | `markets` | `market_created` / `market_updated` deltas for every market; `select_message_types`. |
| [`ws_market_stats.py`](./ws_market_stats.py) | `market_stats` | Price history in the join reply, bucket updates after; `request_series`. |
| [`ws_market_updates.py`](./ws_market_updates.py) | `market_updates` | Changes for the markets you `watch`. |
| [`ws_orders.py`](./ws_orders.py) | `orders:{user_id}` | `all_orders` snapshot, then `new_open_order`; places and cancels a 1-cent order to show the pushes. `--cancel-on-disconnect` arms that control. |
| [`ws_fills.py`](./ws_fills.py) | `fills:{user_id}` | `all_trades` snapshot, then one `trade` per execution. |
| [`ws_positions.py`](./ws_positions.py) | `positions:{user_id}` | `all_positions` snapshot, then `updated_positions` deltas. |
| [`ws_settlements.py`](./ws_settlements.py) | `settlements:{user_id}` | Recent settlements over REST, then `new_settlements` as they happen. |
| [`ws_balances.py`](./ws_balances.py) | `balances:{user_id}` | Balance and fee summary on join, then `update` and `payment_update`. |
| [`ws_account.py`](./ws_account.py) | `account:{user_id}` | All four account snapshots on one join, then everything the per-type channels push. |
| [`ws_user_info.py`](./ws_user_info.py) | `user_info:{user_id}` | Your profile on join, then any change. |

The SDK sends the socket heartbeat, pings each channel on a timer, and reconnects and rejoins with your filters after a drop.

### Long-running

| Script | What it shows |
|---|---|
| [`worker.py`](./worker.py) | The bot skeleton: one socket with `orderbook` for five markets plus your `orders` and `fills`, printing events until Ctrl-C. `--seconds N` bounds the run. |

### Async patterns

| Script | What it shows |
|---|---|
| [`async_parallel_pulls.py`](./async_parallel_pulls.py) | `AsyncSTX` with `asyncio.gather` over independent calls, timing serial against parallel. |
| [`async_with_ws.py`](./async_with_ws.py) | Event-driven pattern: `ticker` pushes, `AsyncSTX` looks the market up over REST. |

All scripts build their client through [`demo_config.py`](./demo_config.py), which reads the configuration below, loads `.env`, checks for credentials, and holds the few helpers the scripts share. Copy it alongside any script you take out of this repo.

## Configuration

| Variable | Purpose |
|---|---|
| `STX_KEY_ID` | Your API key id. |
| `STX_PRIVATE_KEY` | Path to the key's Ed25519 PEM file, or the PEM text itself. |
| `STX_PROFILE` | Optional. A profile name in `~/.stx/credentials` to read the key (and host) from instead of the variables above. |
| `STX_REGION` | `us` or `ontario`. Default: `us`. |
| `STX_ENV` | `demo` or `production`. Default: `demo`. |
| `STX_HOST` | Optional. A hostname or URL that overrides `STX_REGION` and `STX_ENV` entirely. |

The SDK reads these variables itself, with explicit constructor arguments taking precedence over the environment and the environment over a profile in `~/.stx/credentials`. Accounts and API keys do not carry across exchanges: a key issued for the US demo does not authenticate against the Ontario one.

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
