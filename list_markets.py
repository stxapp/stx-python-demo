"""List the most-active OPEN markets: the kind of view a trader opens
to find something to bet on.

Sorts by 24-hour volume and prints a clean table:

    SPORT       TITLE                                 STATUS  PRICE  PROB    24h VOL
    ───────────────────────────────────────────────────────────────────────────────
    Soccer      Chelsea vs Arsenal                    OPEN    0.62   62%    $1,243,820
    ...

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python list_markets.py

Note on field shaping: ``client.markets()`` returns a ``Page[MarketInfo]``;
passing a flat ``Selection(...)`` narrows the per-market response so
you only pay for the fields you need on the wire. For 100-market lists
the narrow form is 10 to 30x smaller than the default schema walk, which matters
once you scale.
"""
from __future__ import annotations  # PEP 604 union syntax in helpers (3.9 compat)

from stx import Selection

from demo_config import make_client

TOP_N = 20


def _fmt_price(p: float | None) -> str:
    return f"{p:.2f}" if p is not None else "  -"


def _fmt_prob(p: float | None) -> str:
    return f"{p * 100:>3.0f}%" if p is not None else "  -"


def _fmt_volume(v: int | None) -> str:
    if v is None:
        return "        -"
    if v >= 1_000_000:
        return f"${v / 1_000_000:>5.1f}M"
    if v >= 1_000:
        return f"${v / 1_000:>5.1f}K"
    return f"${v:>6.0f}"


def main() -> None:
    with make_client() as client:
        client.login()

        # Fetch a healthy slice: server-side filters narrow to currently-
        # tradable markets; client-side sort by volume picks the top N.
        page = client.markets(
            status=["OPEN"],
            trading="TRUE",
            limit=200,
            selections=Selection(
                "market_id", "sport", "title", "status", "price",
                "probability", "volume24h",
            ),
        )

        # Page acts like a list: sort and slice as usual.
        active = sorted(
            (m for m in page if m.volume24h is not None),
            key=lambda m: m.volume24h or 0,
            reverse=True,
        )[:TOP_N]

        print(f"Top {len(active)} active markets (of {page.count} open / tradable)\n")
        header = (
            f"  {'SPORT':<12} {'TITLE':<40} {'STATUS':<8} "
            f"{'PRICE':<6} {'PROB':<5}  {'24h VOL':>9}"
        )
        print(header)
        print("  " + "─" * (len(header) - 2))
        for m in active:
            sport = (m.sport or "-")[:12]
            title = (m.title or "-")[:40]
            print(
                f"  {sport:<12} {title:<40} "
                f"{m.status or '-':<8} {_fmt_price(m.price):<6} "
                f"{_fmt_prob(m.probability):<5} {_fmt_volume(m.volume24h):>9}"
            )


if __name__ == "__main__":
    main()
