# stx-python-demo

Runnable Python examples for trading on STX. Each script is a self-contained workflow — log in, browse markets, place a safe order, stream live updates — that you can copy as the starting point for your own bot or research code.

## Install

The pin and index-urls live in [`requirements.txt`](./requirements.txt) — clone the repo and run:

```bash
git clone https://github.com/stxapp/stx-python-demo.git
cd stx-python-demo

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

`stx-python` is currently in pre-release on TestPyPI. `requirements.txt` always pulls the latest published version (the `--pre` flag enables alpha/beta resolution); once we ship 1.0 to main PyPI the file collapses to a single `stx-python` line.

If you'd rather not clone, `pip install -r https://raw.githubusercontent.com/stxapp/stx-python-demo/main/requirements.txt` works too.

## Examples

All read from `STX_EMAIL` / `STX_PASSWORD` (set them in your shell or copy [`.env.example`](./.env.example) to `.env`). All target Ontario staging by default.

### Getting started

| Script | Scenario |
|---|---|
| [`quickstart.py`](./quickstart.py) | Smallest possible Hello World — log in and pull a few open markets. |
| [`auth_flow.py`](./auth_flow.py) | The three branches every production caller handles: happy login, 2FA challenge, manual token refresh. |

### Read-only data

| Script | Scenario |
|---|---|
| [`list_markets.py`](./list_markets.py) | Top-N most-active OPEN markets in a clean table — what you'd open to find something to trade. |
| [`account_overview.py`](./account_overview.py) | Balances, loyalty tier, per-market position stats. |
| [`history_pulls.py`](./history_pulls.py) | Paginated `orders` / `trades` / `settlements` — uses `Page[T]` semantics. |

### Trading

| Script | Scenario |
|---|---|
| [`safe_order_round_trip.py`](./safe_order_round_trip.py) | Place a 1¢ LIMIT BUY (never fills), verify it appears in history, cancel it. Try/finally cleanup. |

### WebSocket streaming — markets channel

The broadcast `markets` channel supports server-side filtering on `fields`, `rule_filters`, and `message_types`, plus dynamic re-selection after join. Each script is a 30-second listener focused on one capability.

| Script | Scenario |
|---|---|
| [`ws_markets_basic.py`](./ws_markets_basic.py) | Default join — every field, every rule, both message types. |
| [`ws_markets_bids_offers.py`](./ws_markets_bids_offers.py) | Narrow `fields` to `["bids", "offers"]` for liquidity-only feeds. |
| [`ws_markets_rule_filters.py`](./ws_markets_rule_filters.py) | Server-side filter to specific market rule types (e.g. `spread`, `home_winner`). |
| [`ws_markets_message_types.py`](./ws_markets_message_types.py) | Receive only `market_updated` events; skip `market_created`. |
| [`ws_markets_dynamic.py`](./ws_markets_dynamic.py) | Change filters mid-stream via `ws.push(...)` — `select_fields`, `select_rule_filters`. |
| [`ws_markets_order_book.py`](./ws_markets_order_book.py) | Pin to one market_id and render its top-of-book. Auto-discovers an OPEN market if `STX_MARKET_ID` is unset. |
| [`ws_markets_multi_order_book.py`](./ws_markets_multi_order_book.py) | Maintain a dict of order books for every market matching a rule filter. |

### WebSocket streaming — user streams

| Script | Scenario |
|---|---|
| [`ws_personal_stream.py`](./ws_personal_stream.py) | Subscribe to per-user `PORTFOLIO` + `ORDERS` (auto-scoped to your uid). |

### Async patterns

| Script | Scenario |
|---|---|
| [`async_parallel_pulls.py`](./async_parallel_pulls.py) | `AsyncSTX` + `asyncio.gather` over independent ops — shows the speedup vs serial. |
| [`async_with_ws.py`](./async_with_ws.py) | Event-driven bot pattern: WebSocket pushes events, `AsyncSTX` reacts via HTTP. |

## Configuration

| Variable | Purpose |
|---|---|
| `STX_EMAIL` | Your STX account email. |
| `STX_PASSWORD` | Your STX account password. |
| `STX_REGION` | `ontario` or `us` — overrides the per-script default. |
| `STX_ENV` | `production` / `staging` / `demo` / `dev` / `qa` — overrides the per-script default. |

`STX_HOST` overrides region/env entirely if you need to point at a custom host.

## Continuous integration

GitHub Actions runs every example end-to-end against Ontario staging on every push to `main` — see [`.github/workflows/smoke.yml`](./.github/workflows/smoke.yml). Failures mean either the SDK or the API contract drifted.

Credentials used by CI live as repository secrets; no real credentials ever hit the repo.

## Contributing a recipe

1. Write a self-contained script at the repo root.
2. Read credentials from env vars — never hardcode.
3. Add a row to the table above describing the scenario.
4. Extend [`.github/workflows/smoke.yml`](./.github/workflows/smoke.yml) to run it in CI.

## License

MIT. See [LICENSE](./LICENSE).

## Related

- Developer docs: the official docs site for quickstart, authentication, trading, and WebSocket guides.
- Issues: report bugs or request examples via the [Issues](https://github.com/stxapp/stx-python-demo/issues) tab.
