# STX sample app (Python)

A small web app that acts for STX members, built with [FastAPI](https://fastapi.tiangolo.com) and the [`stx-python`](https://pypi.org/project/stx-python/) SDK (0.8 or later). Copy it as the starting point for your own app.

It does the whole job of an STX app:

- **Sign in with your STX account**, or **connect your STX account** to the app's own login. One setting picks which.
- Keeps each member's tokens on the server, encrypted at rest, and lets the SDK refresh them.
- A **dashboard** of the member's balance, positions, open orders, fills and settlements.
- **Places and cancels orders** for the member.
- Lists **markets** and streams a **live order book and ticker** on the app's own token, with no member involved.
- Streams the member's **live account** (balance, open orders, fills, positions) to the browser.
- **Disconnects** (revokes the grant at STX and deletes the tokens).
- Shows a clear page for each way STX can say no: the member disconnected the app, new STX terms to accept, an account still being verified, a server off the IP allow-list, a scope the member did not allow, an order STX refused, and a feature the exchange does not offer.

Server-side only: the client secret and every token stay on your server, and the browser talks to your app alone.

## Two login modes

Set `LOGIN_MODE` to pick how members get in:

| `LOGIN_MODE` | For | How it works | Code |
|---|---|---|---|
| `stx` | A new app with no login of its own | "Sign in with your STX account" signs the member in to your app and connects their STX account in one step (OpenID Connect). Your user record is keyed on the member's STX id. Live example: [playbook.sportsxapp.com](https://playbook.sportsxapp.com) | [`sample/login_stx.py`](sample/login_stx.py) |
| `own` | An app that already has users and a login | Members sign in with your login (here a stand-in: a name, no password), then "Connect your STX account" (OAuth 2.0, authorization code with PKCE). Live example: [sideline.sportsxapp.com](https://sideline.sportsxapp.com) | [`sample/login_own.py`](sample/login_own.py) |

Everything else is the same in both modes.

## Files

| File | What it does |
|---|---|
| [`sample/main.py`](sample/main.py) | The app and the routes both modes share: markets, dashboard, place and cancel, disconnect, error pages |
| [`sample/login_stx.py`](sample/login_stx.py) | `LOGIN_MODE=stx`: `/login` and `/callback` with `oauth.AsyncConnect` |
| [`sample/login_own.py`](sample/login_own.py) | `LOGIN_MODE=own`: the stand-in login, `/connect` and `/callback` with `oauth.AsyncOAuthClient` |
| [`sample/live.py`](sample/live.py) | Live order book, ticker and account, relayed from STX sockets to the browser as server-sent events |
| [`sample/store.py`](sample/store.py) | SQLite: users, the SDK's token store and pending sign-in store, tokens encrypted with AES-GCM |
| [`sample/errors.py`](sample/errors.py) | One page per SDK exception |
| [`sample/context.py`](sample/context.py), [`sample/config.py`](sample/config.py) | Shared helpers and settings |
| [`sample/templates/`](sample/templates/), [`sample/static/`](sample/static/) | Jinja pages, a little CSS and the JavaScript for the live views |
| [`tests/`](tests/) | Unit tests, with the exchange faked |

## Get credentials

1. Sign up at [apps.stxapp.io](https://apps.stxapp.io) (STX Apps), create your organization and register an app on the **demo** environment. You also get a demo member account with test funds to connect.
2. Choose **Web app** as the application type. You get a `client_id` and a `client_secret`. The secret is shown once: keep it.
3. Add the callback URL `http://localhost:8765/callback`. A `localhost` callback matches on any port, so another local port works too.
4. Allow these scopes: `profile.read balance.read portfolio.read orders.read orders.write` for members, `market_data` for the app's own token, and `openid` for `LOGIN_MODE=stx`.
5. Add your public IP address to the app's IP allow-list. STX takes orders from an app only from listed addresses; reads work from anywhere.

[Apps](https://docs.stxapp.io/apps/) and [OAuth](https://docs.stxapp.io/oauth/) explain each step.

## Run it

Python 3.9 or later.

```bash
git clone https://github.com/stxapp/stx-python-demo.git
cd stx-python-demo/examples/app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then fill in your client id, secret and the two random values
uvicorn sample.main:create_app --factory --env-file .env --port 8765
```

Open <http://localhost:8765>. The app talks to the US demo exchange unless you set `STX_REGION` and `STX_ENV` (or `STX_HOST`).

| Setting | What it is |
|---|---|
| `STX_OAUTH_CLIENT_ID`, `STX_OAUTH_CLIENT_SECRET` | Your app's credentials from STX Apps |
| `STX_OAUTH_REDIRECT_URI` | Your callback URL, exactly as registered |
| `LOGIN_MODE` | `stx` or `own` |
| `STX_REGION`, `STX_ENV`, `STX_HOST` | The exchange. Defaults to `us` and `demo` |
| `MEMBER_SCOPES` | The member scopes to ask for |
| `SESSION_SECRET` | Signs the session cookie |
| `TOKEN_ENCRYPTION_KEY` | 32 random bytes, base64: encrypts tokens at rest. Unset, tokens are stored as they are |
| `DATABASE` | The SQLite file |

## Try it

1. **Markets** lists open markets. Open one to watch its order book and ticker update live. This uses the app's own token, so it works before anyone signs in.
2. Sign in: **Sign in with your STX account** (`stx`), or **Sign in** and then **Connect your STX account** (`own`). STX asks you to log in with your demo member account and to allow the app.
3. The **dashboard** shows your STX account. The balance and open orders update live.
4. On a market page, place a limit order: a buy at `0.01` for 1 contract rests on the book without trading. It appears on the dashboard. **Cancel** removes it.
5. **Disconnect STX** revokes the app's access at STX. The dashboard then offers to connect again.

## How it works

One `AsyncOAuthClient` is built at startup from the exchange's discovery document, and one app client on it reads the market catalog:

```python
app = await oauth.AsyncOAuthClient.discover(
    client_id=..., client_secret=..., redirect_uri=..., scope=member_scopes, region="us", env="demo"
)
catalog = app.app_client("market_data")
markets = await catalog.markets(status="open", trading=True, limit=25)
```

`LOGIN_MODE=own` connects a member with `begin_authorization` and, on the callback, `read_callback` then `redeem_authorization`. The app checks the sign-in was started by the same signed-in user before it exchanges the code:

```python
auth = await app.begin_authorization(pending, data={"user_id": user["id"]})  # redirect to auth.url
...
result = await oauth.read_callback(pending, dict(request.query_params), authorize_endpoint=app.endpoints["authorize"])
done = await app.redeem_authorization(result, store=tokens, member_key=str(user["id"]))
```

`LOGIN_MODE=stx` uses `oauth.AsyncConnect`, which adds a nonce and verifies the ID token:

```python
started = await connect.start()  # redirect to started.url; keep started.saved() server-side
done = await connect.finish(dict(request.query_params), saved)
user = find_or_create(stx_sub=done.identity.sub)
tokens.set(str(user["id"]), done.tokens.to_stored())
```

Then every member call goes through a member client, which refreshes the token when due and saves the new pair in the token store:

```python
async with app.member_client(tokens, str(user["id"])) as member:
    balance = await member.balance()
    order = await member.place_order(market_id, "buy", "limit", price="0.01", quantity="1")
    await member.cancel_order(order.id)
```

STX sockets authenticate with a token in a header, which a browser cannot send and should never hold. So `sample/live.py` opens the socket on the server, `ws.orderbook()` and `ws.ticker()` on the app token and `ws.account_view()` on the member's, and relays each change to the page as a server-sent event.

## When STX says no

Each SDK exception has its own page ([`sample/errors.py`](sample/errors.py)):

| Exception | When | The page |
|---|---|---|
| `oauth.STXGrantRevokedException` | The member disconnected the app in STX, or the connection expired. The SDK has deleted the tokens | Connect again |
| `stx.STXTermsRequiredException` | New STX terms are in effect. Reads and cancels still work; orders wait | A link to the STX terms page that brings the member back to the dashboard (`oauth.terms_url_with_return`) |
| `oauth.STXAccountPendingException` | The member's STX account is still being verified | Try again later |
| `stx.STXIpNotAllowedException` | An order from an address not on the app's IP allow-list | Add the address in STX Apps |
| `stx.STXInsufficientScopeException` | A call needs a scope the member did not allow | Connect again and allow it. A dashboard section shows this inline instead |
| `stx.STXRejectedException` | STX refused the order (a closed market, a bad price) | STX's reason |
| `oauth.STXAccessDeniedException`, `oauth.STXTermsNotAcceptedException`, `oauth.STXOAuthException` | The member did not finish connecting, or the callback was not valid | Start again |
| `stx.STXNotAvailableError` | The exchange does not offer OAuth (or another feature) yet | Which feature and exchange. Try `STX_REGION=ontario` to see it |

## Tests

```bash
python -m unittest discover tests
```

The tests run the SDK's real OAuth code against a fake token endpoint and fake member and app clients, so they need no credentials and make no network calls. The [App](../../.github/workflows/app.yml) workflow also boots the app against US demo in both modes and reads the market list and live order book on an app token.

## Before production

- Serve the app over HTTPS and register an `https` callback URL.
- Set `SESSION_SECRET` and `TOKEN_ENCRYPTION_KEY` from your secret store.
- Replace the stand-in login with your own, and SQLite with your database. When several processes share the token store, give it a `lock(member_key)` so only one refreshes a member at a time (see [Apps: connect members](https://docs.stxapp.io/sdks/python/apps/)).
- The app opens one STX socket per open page. A busy app shares one socket per member and per market.

More in the [Python SDK guide](https://docs.stxapp.io/sdks/python/).
