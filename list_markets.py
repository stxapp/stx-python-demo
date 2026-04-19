"""List STX markets with progressively richer selections — shows the
GraphQL response-shaping advantage over REST SDKs.

Requires stx-python installed (see README.md). Run:

    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python list_markets.py

Compatible with stx-python >= 0.1.0a1.
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
        # REST /markets endpoint.  Use this if you want everything and
        # don't care about payload size.
        wide = client.marketInfos()
        wide_size = len(str(wide))
        print(f"Default (all scalar fields):  {len(wide)} markets, ~{format_bytes(wide_size)}")

        # Print the first market from each to show shape differences.
        print()
        print("Shape comparison for first market:")
        print(f"  Narrow:  {narrow[0]}")
        print(f"  Medium:  {medium[0]}")
        print(f"  Default: {list(wide[0].keys())}")


if __name__ == "__main__":
    main()
