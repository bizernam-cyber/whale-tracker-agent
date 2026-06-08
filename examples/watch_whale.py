"""Example: Watch and monitor a whale wallet."""

import asyncio
from whale_tracker.agent import WhaleTracker


async def main():
    tracker = WhaleTracker()

    # Vitalik's address
    address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

    # Add to watch list
    await tracker.watch(address, chain="ethereum", label="Vitalik")

    # Scan recent activity
    result = await tracker.scan(address, chain="ethereum", days=7)
    print(f"Transactions: {result['transaction_count']}")
    print(f"Patterns: {len(result['patterns'])}")

    for p in result["patterns"]:
        print(f"  [{p['type']}] {p['description']}")

    if result["analysis"]:
        print(f"\nAnalysis:\n{result['analysis']}")


if __name__ == "__main__":
    asyncio.run(main())
