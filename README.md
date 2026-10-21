# STX Python demo

[![Smoke](https://github.com/stxapp/stx-python-demo/actions/workflows/smoke.yml/badge.svg)](https://github.com/stxapp/stx-python-demo/actions/workflows/smoke.yml) [![CI](https://github.com/stxapp/stx-python-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/stxapp/stx-python-demo/actions/workflows/ci.yml)

Small, commented scripts that list markets, place and cancel an order, stream live prices and your account, buy and cash out a combo, and read your portfolio on the [STX](https://stxapp.io) exchange, using the [`stx-python`](https://pypi.org/project/stx-python/) SDK.

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

`python examples/markets.py` lists markets that are open and accepting orders, with the best bid (the highest) and the best offer (the lowest) on each. Code: [`examples/markets.py`](examples/markets.py).

```text
Los Angeles Dodgers at Milwaukee Brewers: Will the Los Angeles Dodgers defeat the Milwaukee Brewers?  bid -  offer -
Los Angeles Dodgers at Milwaukee Brewers: Will the Milwaukee Brewers defeat the Los Angeles Dodgers?  bid -  offer -
Los Angeles Dodgers at Milwaukee Brewers: Will the Los Angeles Dodgers defeat the Milwaukee Brewers?  bid -  offer -
Los Angeles Dodgers at Milwaukee Brewers: Will the Milwaukee Brewers defeat the Los Angeles Dodgers?  bid -  offer -
Cleveland Guardians at Tampa Bay Rays: Will the Cleveland Guardians defeat the Tampa Bay Rays?  bid -  offer -

5 markets shown, more available.
```

Each line is the event and the market's question. Prices are dollars per contract: a bid of `0.4200` on a market whose winning contract pays `1.0000` means a buyer will pay 42 cents for a contract that pays $1 if the answer is yes. `-` means nobody is bidding or offering. Some markets pay `100.0000` for a winning contract, so their prices read like `16.0000`, as on this line from the Ontario demo exchange:

```text
US Confirmation of Aliens in 2027: Will the US confirm that aliens exist before 2027?  bid 16.0000  offer 24.0000
```

Each market's `max_price` says which.

### Place and cancel an order

`python examples/trade.py` places one buy order for 1 contract, reads it back, then cancels it. Code: [`examples/trade.py`](examples/trade.py).

The price is 1% of what a winning contract pays, read from the market's `max_price` (one cent on a $1 contract, `1.00` on a $100 one), and the script only picks a market whose event has not started and where nobody is offering at that price or lower. The order rests on the book and does not trade, and the script cancels it before it exits.

It uses the first such market it finds. To look only at one sport, set `SPORT`, for example `SPORT=Football python examples/trade.py`. `examples/live.py` reads `SPORT` too, so the two scripts still watch the same market.

```text
Market:  Los Angeles Dodgers at Milwaukee Brewers: Will the Los Angeles Dodgers defeat the Milwaukee Brewers?
         STXMLB-26OCT182000LADMIL-GAMELAD  (a winning contract pays 1.0000)
Placed:  buy 1 @ 0.01  id 08ee5eca-c5e5-404d-b305-0aa034e193d7  status accepted
Read:    status open  filled 0.00 of 1.00  client id demo-524b760f-eee9-42b6-8ea5-8adda7b45451
Cancel:  08ee5eca-c5e5-404d-b305-0aa034e193d7  cancelled
Final:   status cancelled  filled 0.00
```

The order carries a `client_order_id`, your own id for it. If a call to place an order fails without an answer, look the order up by that id before placing it again; [Trading](https://docs.stxapp.io/sdks/python/trading/) explains why. The script does that lookup before it cancels, and it cancels whatever happens after the order is sent, so it never leaves an order on the book. It exits non-zero if the order is refused or does not end cancelled.

### Stream prices and your account

`python examples/live.py` opens one WebSocket, streams the order book of the market `examples/trade.py` uses together with your live account (balance, open orders, fills and positions), and exits after 30 seconds. `python examples/live.py 60` streams for 60; the run below used 20. Code: [`examples/live.py`](examples/live.py).

Run `python examples/trade.py` in a second terminal while it streams to see the order arrive on the book and on your account, and leave both when it is cancelled:

```text
Watching Los Angeles Dodgers at Milwaukee Brewers: Will the Los Angeles Dodgers defeat the Milwaukee Brewers?
[book]    best bid -  best offer -  (starting snapshot)
[account] available 100000.0000  open orders 0  positions 0

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

### Buy and cash out a combo

`python examples/combos.py` buys a small combo as a player and then cashes it out, so the run ends holding nothing. Code: [`examples/combos.py`](examples/combos.py). Combos run on the US demo exchange (`region = us`, `env = demo`); on any other exchange the script says so and exits.

A combo is one market over two or more legs, and it pays only if every leg wins. The script picks two open markets from different events that have not started, asks makers to quote on a stake of `2.00`, prints each quote as it arrives (what you would win on that stake), and accepts the best one at its exact amount. The exchange then places your order on the combo's own market. The script cashes out the same way: it asks makers what they pay for everything you hold, accepts the best quote, and checks your position is back to zero.

It waits up to 20 seconds for each quote and says so if none arrives; `python examples/combos.py 60` waits up to 60. Set the stake and number of legs with `STAKE=5 LEGS=3 python examples/combos.py`, and look only at one sport with `SPORT=Football python examples/combos.py`; the run below used `SPORT=Football`.

```text
Leg 1:   Will the Sam Houston Bearkats defeat the New Mexico State Aggies?  (NMSU @ SHSU)
Leg 2:   Will the App State Mountaineers defeat the James Madison Dukes?  (JMU @ APP)

Request: 6fb0aceb-dde1-4f30-9b67-06442349cb18  stake 2.00
Waiting up to 20 s for a quote...
[quote]  win 3.0000 on a 2.00 stake  (quote 76242ebd-1f1f-4fbe-b4e3-cb4e6abe9842)
Bought:  5.00 @ 0.4000  order 415741fe-4b20-4632-a5c3-b3c571a8e092  (accepted win 3.0000)
         combo d9295f11-1cc5-494f-8851-1f0fd06ce572  Won / Won  (a winning contract pays 1.0000)

Cash out: 2f439ebc-616a-438d-aabb-bb57e59a531a  selling 5.00
[quote]  pays 1.7500 for all 5.00  (quote f18ce8e9-1dda-48ec-b715-49a63b64cea6)
Sold:    5.00 @ 0.3500  order 7c90f4c1-f3db-4f1f-8b70-a08d0046d0b7  (accepted 1.7500)
Final:   position 0.00 on the combo  open orders 0
```

Quotes are amounts, not prices: the exchange derives the price and size of your order from your stake and the amount you accept. Above, a `2.00` stake against a `3.00` win prices at 2 / (2 + 3) = `0.4000`, for 5 contracts that pay `5.00` if both legs win. The cash out sold all 5 for the `1.75` the maker quoted. Like `examples/live.py`, this script uses `AsyncSTX`, because the WebSocket client is asyncio. [Combos](https://docs.stxapp.io/sdks/python/combos/) walks through every call, including the maker side, and [Combo negotiation](https://docs.stxapp.io/websockets/channels/combo-negotiation/) documents the protocol.

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

The [Smoke](.github/workflows/smoke.yml) workflow also runs every example against the US and Ontario demo exchanges (combos on US demo only) on each pull request, each push to `main` and once a day.

## Documentation

- [Python SDK guide](https://docs.stxapp.io/sdks/python/)
- [API reference](https://docs.stxapp.io/sdks/python/reference/)
- [Support](https://docs.stxapp.io/support/)

MIT license. Use of the STX API and exchange is subject to the STX terms of use and privacy policy: United States ([terms of use](https://stxapp.io/legal/terms-of-use.pdf), [privacy policy](https://stxapp.io/legal/privacy-policy.pdf)), Ontario ([terms of use](https://stxapp.ca/legal/terms-of-use.pdf), [privacy policy](https://stxapp.ca/legal/privacy-policy.pdf)).
