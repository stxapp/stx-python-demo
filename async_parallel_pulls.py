"""Parallelise unrelated reads with ``AsyncSTX`` and ``asyncio.gather``.

When a view needs data from several independent calls (markets for two
sports and your recent orders, say), fire them together instead of one
after another. One ``AsyncSTX`` holds one connection pool, so each extra
request costs a round trip, not a new connection.

Run:
    export STX_KEY_ID="your-key-id"
    export STX_PRIVATE_KEY="$HOME/.stx/us-demo.pem"
    python async_parallel_pulls.py
"""

import asyncio
import time

from demo_config import make_async_client


async def main() -> None:
    async with make_async_client() as client:
        await client.me()  # warm the connection so both timings start equal

        def calls():
            return (
                client.markets(sports=["Baseball"], status="open", limit=25),
                client.markets(sports=["Football"], status="open", limit=25),
                client.orders(limit=5),
            )

        t0 = time.perf_counter()
        for call in calls():
            await call
        serial = time.perf_counter() - t0

        t0 = time.perf_counter()
        results = await asyncio.gather(*calls(), return_exceptions=True)
        parallel = time.perf_counter() - t0

        for label, r in zip(("baseball markets", "football markets", "orders"), results):
            if isinstance(r, Exception):
                print(f"  {label:<18} failed: {type(r).__name__}: {r}")
            else:
                print(f"  {label:<18} {len(r)} rows")
        print(f"\n  serial:   {serial * 1000:>6.0f} ms")
        print(f"  parallel: {parallel * 1000:>6.0f} ms")


if __name__ == "__main__":
    asyncio.run(main())
