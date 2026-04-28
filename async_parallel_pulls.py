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
        await client.login(params={})

        # Serial baseline — three independent ops, one after another.
        t0 = time.perf_counter()
        m1 = await client.markets(
            params={"input": {"sports": ["Soccer"], "limit": 25}},
            selections=Selection("market_id", "title"),
        )
        m2 = await client.markets(
            params={"input": {"sports": ["Basketball"], "limit": 25}},
            selections=Selection("market_id", "title"),
        )
        acct = await client.account(
            selections=Selection("available_balance", "loyalty_tier")
        )
        serial = time.perf_counter() - t0

        # Parallel — same three ops scheduled concurrently. The session
        # multiplexes them over the kept-alive aiohttp connection.
        t0 = time.perf_counter()
        m1p, m2p, acctp = await asyncio.gather(
            client.markets(
                params={"input": {"sports": ["Soccer"], "limit": 25}},
                selections=Selection("market_id", "title"),
            ),
            client.markets(
                params={"input": {"sports": ["Basketball"], "limit": 25}},
                selections=Selection("market_id", "title"),
            ),
            client.account(selections=Selection("available_balance", "loyalty_tier")),
        )
        parallel = time.perf_counter() - t0

        print(
            f"Soccer: {len(m1)} markets   "
            f"Basketball: {len(m2)} markets   "
            f"Balance: ${acctp.available_balance or 0:.2f}"
        )
        print(f"\n  serial:   {serial * 1000:>6.0f} ms")
        print(f"  parallel: {parallel * 1000:>6.0f} ms")
        if serial > 0:
            print(f"  speedup:  {serial / parallel:.2f}×")
        # Sanity — same data shape returned both ways.
        assert len(m1) == len(m1p) and len(m2) == len(m2p)


if __name__ == "__main__":
    asyncio.run(main())
