// Live updates from this server's /live/* endpoints (server-sent events).
// The server holds the STX tokens and sockets; the browser only listens.

function cell(text) {
  const td = document.createElement("td");
  td.textContent = text == null ? "-" : text;
  return td;
}

function fillBook(id, levels) {
  const body = document.getElementById(id);
  body.replaceChildren(...levels.map((lv) => {
    const tr = document.createElement("tr");
    tr.append(cell(lv.price), cell(lv.quantity));
    return tr;
  }));
}

function status(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

const market = document.getElementById("live-market");
if (market) {
  const id = market.dataset.marketId;
  const feed = new EventSource(`/live/market/${id}?sport=${encodeURIComponent(market.dataset.sport)}`);
  feed.addEventListener("joined", () => status("market-status", "live"));
  feed.addEventListener("book", (e) => {
    const book = JSON.parse(e.data);
    fillBook("bids", book.bids);
    fillBook("offers", book.offers);
  });
  feed.addEventListener("ticker", (e) => {
    const t = JSON.parse(e.data);
    status("ticker", `bid ${t.best_bid ?? "-"} · offer ${t.best_offer ?? "-"} · last ${t.last_traded_price ?? "-"} · volume ${t.total_volume ?? "-"}`);
  });
  feed.onerror = () => status("market-status", "reconnecting…");
}

const account = document.getElementById("live-account");
if (account) {
  const titles = JSON.parse(document.getElementById("titles")?.textContent || "{}");
  const feed = new EventSource("/live/account");

  function show(state) {
    status("available", state.available_balance);
    status("account-balance", state.account_balance);
    const body = document.getElementById("open-orders");
    if (!state.open_orders.length) {
      const tr = document.createElement("tr");
      const td = cell("No open orders.");
      td.colSpan = 7;
      tr.append(td);
      body.replaceChildren(tr);
      return;
    }
    body.replaceChildren(...state.open_orders.map((o) => {
      const tr = document.createElement("tr");
      tr.append(cell(titles[o.market_id] || o.market_id), cell(o.action), cell(o.price), cell(o.quantity), cell(o.filled), cell(o.status));
      const td = document.createElement("td");
      const form = document.createElement("form");
      form.method = "post";
      form.action = `/orders/${o.id}/cancel`;
      const button = document.createElement("button");
      button.className = "small";
      button.textContent = "Cancel";
      form.append(button);
      td.append(form);
      tr.append(td);
      return tr;
    }));
  }

  feed.addEventListener("snapshot", (e) => {
    status("account-status", "live");
    show(JSON.parse(e.data));
  });
  feed.addEventListener("change", (e) => {
    const change = JSON.parse(e.data);
    show(change);
    status("account-change", `Last update: ${change.kind} (${change.event}) at ${new Date().toLocaleTimeString()}. Reload for full history.`);
  });
  feed.addEventListener("ended", (e) => {
    feed.close();
    status("account-status", "disconnected");
    if (JSON.parse(e.data).reason === "grant_revoked") window.location.reload();
  });
  feed.onerror = () => status("account-status", "reconnecting…");
}
