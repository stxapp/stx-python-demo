# STX Python demo

[![Smoke](https://github.com/stxapp/stx-python-demo/actions/workflows/smoke.yml/badge.svg)](https://github.com/stxapp/stx-python-demo/actions/workflows/smoke.yml) [![CI](https://github.com/stxapp/stx-python-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/stxapp/stx-python-demo/actions/workflows/ci.yml)

Small, commented scripts that list markets, place and cancel an order, stream live prices and your account, and read your portfolio on the [STX](https://stxapp.io) exchange, using the [`stx-python`](https://pypi.org/project/stx-python/) SDK.

## Before you start

- Python 3.9 or later.
- An API key for the STX exchange you are building against. [Environments](https://docs.stxapp.io/environments/) lists the exchanges and where to get a key. Start on a demo exchange. Placing orders needs a `read_write` key.

## Setup

```bash
git clone https://github.com/stxapp/stx-python-demo.git
cd stx-python-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Give the scripts your API key in one of two ways. [Authentication](https://docs.stxapp.io/sdks/python/authentication/) covers both in full.

A profile in `~/.stx/credentials`, with the region and env of your exchange from [Environments](https://docs.stxapp.io/environments/):

```ini
[default]
region   = us
env      = demo
key_id   = your-key-id
key_file = ~/.stx/stx-key.pem
```

To keep several profiles, name each section and pick one with `STX_PROFILE`, for example `STX_PROFILE=my-demo python examples/markets.py`.

Or environment variables:

```bash
export STX_REGION=us STX_ENV=demo
export STX_KEY_ID=your-key-id
export STX_PRIVATE_KEY=~/.stx/stx-key.pem   # a path, or the PEM text
```

The scripts never print your key.

## Examples

Each script is in [`examples/`](examples/) and runs with one command. The sample output below comes from the US demo exchange (`region = us`, `env = demo`). Yours will show the markets open when you run it.

### List markets

`python examples/markets.py` lists markets that are open and accepting orders, with the best bid and offer on each. Code: [`examples/markets.py`](examples/markets.py).

```text
New York Yankees at San Diego Padres: Yankees First Run  bid 0.4200  offer -
New York Yankees at San Diego Padres: Padres First Run  bid -  offer -
Norfolk State Spartans at Old Dominion Monarchs: Norfolk St Score Last  bid -  offer -
Norfolk State Spartans at Old Dominion Monarchs: Old Dominion Score Last  bid -  offer -
Florida International Panthers at Florida Atlantic Owls: First Score a TD  bid -  offer -

5 markets shown, more available.
```

Prices are dollars per contract. A bid of `0.4200` on a market whose winning contract pays `1.0000` means a buyer will pay 42 cents for a contract that pays $1 if the Yankees score first. `-` means nobody is bidding or offering. Some markets pay `100.0000` for a winning contract, so their prices read like `42.0000`. Each market's `max_price` says which.

### Place and cancel an order

`python examples/trade.py` places one buy order for 1 contract, reads it back, then cancels it. Code: [`examples/trade.py`](examples/trade.py).

The price is 1% of what a winning contract pays, read from the market's `max_price` (one cent on a $1 contract, `1.00` on a $100 one), and the script only picks a market whose event has not started and where nobody is offering at that price or lower. The order rests on the book and does not trade, and the script cancels it before it exits.

It uses the first such market it finds. To look only at one sport, set `SPORT`, for example `SPORT=Football python examples/trade.py`. `examples/live.py` reads `SPORT` too, so the two scripts still watch the same market.

```text
Market:  Chicago White Sox at Houston Astros: MLB Playoff CHW @ HOU
         STXMLB-26OCT011700CHWHOU-GAMECHW  (a winning contract pays 1.0000)
Placed:  buy 1 @ 0.01  id a6907ba5-0dd1-4502-97b8-4a14de297895  status accepted
Read:    status open  filled 0.00 of 1.00  client id demo-8c629659-2bc8-49c7-b09d-82c634e0bc85
Cancel:  a6907ba5-0dd1-4502-97b8-4a14de297895  cancelled
Final:   status cancelled  filled 0.00
```

The order carries a `client_order_id`, your own id for it. If a call to place an order fails without an answer, look the order up by that id before placing it again; [Trading](https://docs.stxapp.io/sdks/python/trading/) explains why. The script does that lookup before it cancels, and it cancels whatever happens after the order is sent, so it never leaves an order on the book. It exits non-zero if the order is refused or does not end cancelled.

### Stream prices and your account

`python examples/live.py` opens one WebSocket, streams the order book of the market `examples/trade.py` uses together with your live account (balance, open orders, fills and positions), and exits after 30 seconds. `python examples/live.py 60` streams for 60; the run below used 20. Code: [`examples/live.py`](examples/live.py).

Run `python examples/trade.py` in a second terminal while it streams to see the order arrive on the book and on your account, and leave both when it is cancelled:

```text
Watching Chicago White Sox at Houston Astros: MLB Playoff CHW @ HOU
[book]    best bid -  best offer -  (starting snapshot)
[account] available 10019999.6400  open orders 0  positions 0

Streaming for 20 s. Run examples/trade.py in another terminal to see an order come and go.

[account] positions 1 updated
[account] order buy 1.00 @ 0.0100  open  filled 0.00
[book]    best bid 1.00 @ 0.0100  best offer -
[account] order buy 1.00 @ 0.0100  cancelled  filled 0.00
[account] positions 1 updated
[account] positions 1 updated
[account] order buy 1.00 @ 0.0100  cancelled  filled 0.00
[book]    best bid -  best offer -

Closed. Open orders now: 0
```

The client signs the connection, sends heartbeats and reconnects for you. The WebSocket client is asyncio, so this script uses `AsyncSTX`; the others use the blocking `STX`. The channels and their payloads are described under [WebSockets](https://docs.stxapp.io/sdks/python/websockets/).

### Read your portfolio

`python examples/portfolio.py` prints your key's scope, balance, open positions, open orders and recent fills. Code: [`examples/portfolio.py`](examples/portfolio.py).

```text
Key scope: read_write

Balance: 10019999.6400  available 10019999.6400

Open positions: 0

Open orders: 0

Recent fills: 5
  ee99086e-99b0-4f95-99bc-c93fd1a50118  buy 2.00 @ 0.3600
  5635f7a3-4ef5-417d-9123-b05e11d4307f  buy 1.00 @ 0.4500
  8868999f-f0dc-4278-9b95-2421b50d2c1f  buy 1.00 @ 0.4500
  e82a9a02-fda1-4cc4-ba66-d154581ae290  buy 5.00 @ 0.1000
  7a6e8526-8691-4efa-88e0-8eb7e91fe9c1  sell 1.00 @ 0.6000
```

`positions()` also returns markets you have traded out of, with a position of `0.00`; the script leaves those out. `examples/live.py` shows the same balance and positions as they change.

## Tests

```bash
python -m unittest discover tests
```

The tests cover the helpers in [`examples/helpers.py`](examples/helpers.py) with a stand-in client, so they need no API key and make no network calls.

The [Smoke](.github/workflows/smoke.yml) workflow also runs every example against the US and Ontario demo exchanges on each pull request, each push to `main` and once a day.

## Documentation

- [Python SDK guide](https://docs.stxapp.io/sdks/python/)
- [API reference](https://docs.stxapp.io/sdks/python/reference/)
- [Support](https://docs.stxapp.io/support/)

MIT license. Use of the STX API and exchange is subject to the STX terms of use and privacy policy: United States ([terms of use](https://config.stxapp.io/us/terms_of_use.pdf), [privacy policy](https://config.stxapp.io/us/privacy_policy.pdf)), Ontario ([terms of use](https://config.stxapp.ca/on/terms-of-use.pdf), [privacy policy](https://config.stxapp.ca/on/privacy-policy.pdf)).
