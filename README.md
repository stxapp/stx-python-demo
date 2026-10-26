# STX Python demo

[![Smoke](https://github.com/stxapp/stx-python-demo/actions/workflows/smoke.yml/badge.svg)](https://github.com/stxapp/stx-python-demo/actions/workflows/smoke.yml) [![CI](https://github.com/stxapp/stx-python-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/stxapp/stx-python-demo/actions/workflows/ci.yml)

Small, commented scripts that list markets, place and cancel an order, stream live prices and your account, buy and cash out a combo, quote combos as a maker, and read your portfolio on the [STX](https://stxapp.io) exchange, using the [`stx-python`](https://pypi.org/project/stx-python/) SDK. And a [sample web app](#sample-app) that acts for STX members who sign in with or connect their STX account.

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

`python examples/markets.py` lists the first 5 upcoming markets that are open and accepting orders, with the best bid (the highest) and the best offer (the lowest) on each. Upcoming means the event is scheduled and its start time has not passed: an event can stay open after its start time, and nobody quotes those. Code: [`examples/markets.py`](examples/markets.py).

```text
Manchester United at Como: Will the game between the Como and the Manchester United end in a draw in the 1st Half?  bid 0.3100  offer 0.3600
Galatasaray at Lille: Will the game between the Lille and the Galatasaray end in a draw in the 1st Half?  bid 0.3100  offer 0.3600
Galatasaray at Lille: Will the Galatasaray win the game between the Lille and the Galatasaray in regulation time?  bid 0.3100  offer 0.3600
Galatasaray at Lille: Will the Lille win the game between the Lille and the Galatasaray in the 1st Half?  bid 0.3100  offer 0.3600
Manchester United at Como: Will the game between the Como and the Manchester United end in a draw during regulation?  bid 0.3100  offer 0.3600

5 upcoming markets shown.
```

Each line is the event and the market's question. Prices are dollars per contract: a bid of `0.4200` on a market whose winning contract pays `1.0000` means a buyer will pay 42 cents for a contract that pays $1 if the answer is yes. `-` means nobody is bidding or offering. Some markets pay `100.0000` for a winning contract, so their prices read like `16.0000`, as on this line from the Ontario demo exchange:

```text
US Confirmation of Aliens in 2027: Will the US confirm that aliens exist before 2027?  bid 16.0000  offer 24.0000
```

Each market's `max_price` says which.

### Place and cancel an order

`python examples/trade.py` places one buy order for 1 contract, reads it back, then cancels it. Code: [`examples/trade.py`](examples/trade.py).

The price is 1% of what a winning contract pays, read from the market's `max_price` (one cent on a $1 contract, `1.00` on a $100 one), and the script only picks an upcoming market (as above) where nobody is offering at that price or lower. The order rests on the book and does not trade, and the script cancels it before it exits.

It uses the first such market it finds. To look only at one sport, set `SPORT`, for example `SPORT=Football python examples/trade.py`. `examples/live.py` reads `SPORT` too, so the two scripts still watch the same market.

```text
Market:  Manchester United at Como: Will the game between the Como and the Manchester United end in a draw in the 1st Half?
         STXUEFA-26OCT211245MANCOMO-R1DRAWMANCOMO  (a winning contract pays 1.0000)
Placed:  buy 1 @ 0.01  id bed6edd4-ad0a-4aed-bc99-cc945a702ac4  status accepted
Read:    status open  filled 0.00 of 1.00  client id demo-9cabbbf6-1198-4963-b5cc-a079151b16ea
Cancel:  bed6edd4-ad0a-4aed-bc99-cc945a702ac4  cancelled
Final:   status cancelled  filled 0.00
```

The order carries a `client_order_id`, your own id for it. If a call to place an order fails without an answer, look the order up by that id before placing it again; [Trading](https://docs.stxapp.io/sdks/python/trading/) explains why. The script does that lookup before it cancels, and it cancels whatever happens after the order is sent, so it never leaves an order on the book. It exits non-zero if the order is refused or does not end cancelled.

### Stream prices and your account

`python examples/live.py` opens one WebSocket, streams the order book of the market `examples/trade.py` uses together with your live account (balance, open orders, fills and positions), and exits after 30 seconds. `python examples/live.py 60` streams for 60; the run below used 20. Code: [`examples/live.py`](examples/live.py).

Run `python examples/trade.py` in a second terminal while it streams to see the order arrive on your account and leave when it is cancelled. The book is pushed again each time, but its best bid does not change: a one-cent bid sits below the best one.

```text
Watching Manchester United at Como: Will the game between the Como and the Manchester United end in a draw in the 1st Half?
[book]    best bid 50.00 @ 0.3100  best offer 50.00 @ 0.3600  (starting snapshot)
[book]    best bid 50.00 @ 0.3100  best offer 50.00 @ 0.3600
[account] available 100000.0000  open orders 0  positions 0

Streaming for 20 s. Run examples/trade.py in another terminal to see an order come and go.

[account] positions 1 updated
[account] order buy 1.00 @ 0.0100  open  filled 0.00
[book]    best bid 50.00 @ 0.3100  best offer 50.00 @ 0.3600
[account] order buy 1.00 @ 0.0100  cancelled  filled 0.00
[account] positions 1 updated
[account] positions 1 updated
[account] order buy 1.00 @ 0.0100  cancelled  filled 0.00
[book]    best bid 50.00 @ 0.3100  best offer 50.00 @ 0.3600

Closed. Open orders now: 0
```

The client signs the connection, sends heartbeats and reconnects for you. The WebSocket client is asyncio, so this script uses `AsyncSTX`; the others use the blocking `STX`. The channels and their payloads are described under [WebSockets](https://docs.stxapp.io/sdks/python/websockets/).

### Buy and cash out a combo

`python examples/combos.py` buys a small combo as a player and then cashes it out, so the run ends holding nothing. Code: [`examples/combos.py`](examples/combos.py). Combos run on the US demo and Ontario demo exchanges (`env = demo`, with `region = us` or `region = ontario`); on any other exchange the script says so and exits.

A combo is one market over two or more legs, and it pays only if every leg wins. The script picks two open markets from different events that have not started, asks makers to quote on a stake of `2.00`, prints each quote as it arrives (what you would win on that stake), and accepts the best one at its exact amount. The exchange then places your order on the combo's own market. The script cashes out the same way: it asks makers what they pay for everything you hold, accepts the best quote, and checks your position is back to zero.

It waits up to 20 seconds for each quote and says so if none arrives; `python examples/combos.py 60` waits up to 60. Set the stake and number of legs with `STAKE=5 LEGS=3 python examples/combos.py`, and look only at one sport with `SPORT=Football python examples/combos.py`.

```text
Leg 1:   Will the game between the Como and the Manchester United end in a draw in the 1st Half?  (MAN @ COMO 1H)
Leg 2:   Will the game between the Lille and the Galatasaray end in a draw in the 1st Half?  (GAL @ LILL 1H)

Request: 517a6b14-422e-4cfa-b867-c4fed69b62ae  stake 2.00
Waiting up to 20 s for a quote...
[quote]  win 15.1400 on a 2.00 stake  (quote e512dbbc-1d61-4424-a26c-5e9046f5a3a1)
Bought:  17.00 @ 0.1167  order d6bab3fe-cfc1-497d-92a9-3f3089e52cec  (accepted win 15.1400)
         combo 4582dc69-296c-4ce3-911c-5314b00b93f7  Won / Won  (a winning contract pays 1.0000)

Cash out: df15bc40-0189-4fc2-9e18-722cc85865ff  selling 17.00
[quote]  pays 1.7900 for all 17.00  (quote 6ac317df-5fec-404f-b9b8-9bfa77e72ff0)
Sold:    17.00 @ 0.1052  order 15abcc18-f13b-4674-b0e7-3816b7c72ab3  (accepted 1.7900)
Final:   position 0.00 on the combo  open orders 0
```

Quotes are amounts, not prices: the exchange derives the price and size of your order from your stake and the amount you accept. Above, a `2.00` stake against a `15.14` win prices at 2 / (2 + 15.14) = 0.11669, rounded up to the combo's tick: `0.1167`. That buys 17 whole contracts, which pay `17.00` if both legs win. The cash out sold all 17 for the `1.79` the maker quoted, at 1.79 / 17 = 0.10529, rounded down: `0.1052`. Like `examples/live.py`, this script uses `AsyncSTX`, because the WebSocket client is asyncio. [Combos](https://docs.stxapp.io/sdks/python/combos/) walks through every call, including the maker side, and [Combo negotiation](https://docs.stxapp.io/websockets/channels/combo-negotiation/) documents the protocol.

### Quote combos as a maker

`python examples/combo_maker.py` joins as a maker and quotes every combo request on the exchange until you press Ctrl-C, printing how each one ends. Code: [`examples/combo_maker.py`](examples/combo_maker.py). It runs where combos do, on the US demo and Ontario demo exchanges, and needs a `read_write` key.

Each request arrives as `rfq_opened`. On a buy you quote what the player wins, the stake times `WIN_MULTIPLE` (default `9`); on a cash out you quote what you pay for everything the player sells, `CASH_OUT_PRICE` a contract (default `0.08`). Each quote stands for `QUOTE_SECONDS` (default `30`). The script checks that the amount prices inside the request's `max_price` and `tick_size` before it sends it, and skips the request if not. `python examples/combo_maker.py 120` stops after 120 seconds instead.

This run, on the Ontario demo exchange, quoted a buy and then the player's cash out of the same combo, and won both:

```text
Quoting combos on https://demo.stxapp.ca as a maker.
Buys: win 15x the stake. Cash outs: 0.12 a contract. Each quote stands 30 s. Ctrl-C to stop.

[request]  354cc116  buy, stake 2.0000, 2 legs: WSH @ CHA won, LA @ NYR won
[quoted]   354cc116  win 30.0000  for 30 s  quote d0a4b3bd-e53b-4d26-b901-51af04c6f313
[accepted] 354cc116  quote d0a4b3bd-e53b-4d26-b901-51af04c6f313
[won]      354cc116  order 5c020a30-1cfc-4d57-8f0c-7f51a0d0913f  32.00 @ 0.0625  combo df0489de-8f36-4fde-818e-adeaf038bde3
[closed]   354cc116  placed
[request]  79b805cc  cash out of 32.00 on combo df0489de
[quoted]   79b805cc  pay 3.8400 for 32.00  for 30 s  quote d55d0637-0189-460f-9978-19356747ac48
[accepted] 79b805cc  quote d55d0637-0189-460f-9978-19356747ac48
[won]      79b805cc  order 09159e2a-5545-4996-82d4-d9ad8e81896c  32.00 @ 0.1200  combo df0489de-8f36-4fde-818e-adeaf038bde3
[closed]   79b805cc  placed
```

`[accepted]` is `quote_accepted`: the player took your quote and the exchange is placing both orders. `[won]` is `placed`, with your order on the combo's market at the same price and size as the player's. When another maker quotes the player more, the player takes theirs and your quote ends with `placed_elsewhere`, as in this run at `WIN_MULTIPLE=3 CASH_OUT_PRICE=0.02`:

```text
[request]  7fb32026  buy, stake 2.0000, 2 legs: WSH @ CHA won, LA @ NYR won
[quoted]   7fb32026  win 6.0000  for 30 s  quote bc38ca50-6d36-40fe-8d27-000afd0c04c6
[lost]     7fb32026  quote bc38ca50-6d36-40fe-8d27-000afd0c04c6  placed_elsewhere
[closed]   7fb32026  placed
[request]  a55f671b  cash out of 32.00 on combo df0489de
[quoted]   a55f671b  pay 0.6400 for 32.00  for 30 s  quote a0dc4ae3-9651-4386-b69e-b3441b0883e4
[lost]     a55f671b  quote a0dc4ae3-9651-4386-b69e-b3441b0883e4  placed_elsewhere
[closed]   a55f671b  placed
```

A quote can also end `[expired]`, when its `QUOTE_SECONDS` run out and a later quote on the request replaces it, or with the request's own reason, such as `cancelled`. `[closed]` is `rfq_closed`, sent for every request whether you quoted or not. Other makers quote on the demo exchanges too, so expect to lose some requests. A request your own account opened is refused with `cannot_quote_own_request`. Every socket joined as one account gets the pushes about all of that account's quotes, so run one maker per account. Quotes belong to the connection that placed them: on Ctrl-C, or if the connection drops, they are withdrawn. [Quote combos as a maker](https://docs.stxapp.io/websockets/combo-maker/) covers the maker side in every language, and [Combo negotiation](https://docs.stxapp.io/websockets/channels/combo-negotiation/) documents each frame.

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

## Sample app

[`examples/app/`](examples/app/) is a complete web app, built with FastAPI, for building on STX as an app: members sign in with their STX account (or connect it to your own login), and the app shows their balance, positions, orders, fills and settlements, places and cancels orders for them, streams their account and live order books, and disconnects. It uses OAuth credentials from [STX Apps](https://apps.stxapp.io) rather than an API key. Setup, the two login modes and a map of the code are in its [README](examples/app/README.md).

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

MIT license. Use of the STX API and exchange is subject to the STX terms of use and privacy policy: United States ([terms of use](https://stxapp.io/legal/terms-of-use.pdf), [privacy policy](https://stxapp.io/legal/privacy-policy.pdf)), Ontario ([terms of use](https://stxapp.ca/legal/terms-of-use.pdf), [privacy policy](https://stxapp.ca/legal/privacy-policy.pdf)).
