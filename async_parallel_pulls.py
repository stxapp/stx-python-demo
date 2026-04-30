"""Parallelise unrelated reads with ``AsyncSTX`` + ``asyncio.gather``.

If you need data from several independent ops at once — say, building
a dashboard view that wants markets, account, and order history — fire
them in parallel instead of serialising. ``AsyncSTX`` shares one
``aiohttp`` session, so the cost per extra request is just the round
trip, not a new connection.

Run:
    export STX_EMAIL="you@example.com"
    export STX_PASSWORD="..."
    python async_parallel_pulls.py
"""
import asyncio
import time

from stx import AsyncSTX, Selection


async def main() -> None:
    async with AsyncSTX(region="ontario", env="staging") as client:
        await client.login()

        # Serial baseline — three independent ops, one after another.
        t0 = time.perf_counter()
        m1 = await client.markets(
            sports=["Soccer"], limit=25,
            selections=Selection("market_id", "title"),
        )
        m2 = await client.markets(
            sports=["Basketball"], limit=25,
            selections=Selection("market_id", "title"),
        )
        acct = await client.account(
            selections=Selection("available_balance", "loyalty_tier")
        )
        serial = time.perf_counter() - t0

        # Parallel — same three ops scheduled concurrently. The session
        # multiplexes them over the kept-alive aiohttp connection.
        #
        # `return_exceptions=True` so a single failure on staging (token
        # races during concurrent auth checks, transient 5xx, etc.)
        # doesn't take the whole demo down — we report what came back
        # and what failed instead.
        t0 = time.perf_counter()
        results = await asyncio.gather(
            client.markets(
                sports=["Soccer"], limit=25,
                selections=Selection("market_id", "title"),
            ),
            client.markets(
                sports=["Basketball"], limit=25,
                selections=Selection("market_id", "title"),
            ),
            client.account(selections=Selection("available_balance", "loyalty_tier")),
            return_exceptions=True,
        )
        parallel = time.perf_counter() - t0

        labels = ("soccer-markets", "basketball-markets", "account")
        for label, r in zip(labels, results):
            if isinstance(r, Exception):
                print(f"  {label:<20} failed: {type(r).__name__}: {r}")
            elif label.endswith("markets"):
                print(f"  {label:<20} {len(r)} rows")
            else:
                print(f"  {label:<20} balance=${r.available_balance or 0:.2f}")

        print(f"\n  serial:   {serial * 1000:>6.0f} ms")
        print(f"  parallel: {parallel * 1000:>6.0f} ms")
        if serial > 0:
            print(f"  speedup:  {serial / parallel:.2f}×")


if __name__ == "__main__":
    asyncio.run(main())
