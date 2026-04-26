"""List STX markets with progressively richer selections — shows the
GraphQL response-shaping advantage over REST SDKs.

Requires stx-python installed (see README.md). Run:

    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python list_markets.py

Compatible with stx-python >= 0.1.0a3 (typed Pydantic response models).
"""
from stx import STX, Selection


def format_bytes(b: int) -> str:
    """Tiny human-readable byte formatter, used to highlight the
    payload-size difference between narrow and wide selections."""
    for unit in ("B", "KB", "MB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"


def main() -> None:
    with STX(region="ontario", env="staging") as client:
        client.login(params={})

        # (1) Narrow: the minimum a list view needs. Fast, small payload.
        narrow = client.marketInfos(
            selections=Selection("marketId", "status"),
        )
        narrow_size = len(str(narrow))
        print(f"Narrow  (marketId + status):        {len(narrow)} markets, ~{format_bytes(narrow_size)}")

        # (2) Medium: a realistic list-view slice.
        medium = client.marketInfos(
            selections=Selection(
                "marketId",
                "status",
                "title",
                "sport",
                "price",
                "volume24h",
            ),
        )
        medium_size = len(str(medium))
        print(f"Medium  (+ title/sport/price/vol):  {len(medium)} markets, ~{format_bytes(medium_size)}")

        # (3) Default: no selections → every scalar field. Acts like a
        # REST /markets endpoint. Capped at 50 markets here because the
        # full all-fields walk over the entire orderbook is heavy enough
        # to time out on staging/dev gateways. In your own code, pass
        # `limit` (or other MarketInfosInput filters) sized to your
        # actual workload.
        wide = client.marketInfos(params={"input": {"limit": 50}})
        wide_size = len(str(wide))
        print(f"Default (all scalar fields):  {len(wide)} markets, ~{format_bytes(wide_size)}")

        # Print the first market from each to show shape differences.
        # marketInfos() returns List[MarketInfo] — Pydantic models, not
        # dicts. They print themselves nicely; for the field-set use
        # .model_fields_set (the set of fields actually populated by
        # the Selection).
        print()
        print("Shape comparison for first market:")
        print(f"  Narrow:  {narrow[0]}")
        print(f"  Medium:  {medium[0]}")
        print(f"  Default: {sorted(wide[0].model_fields_set)}")


if __name__ == "__main__":
    main()
