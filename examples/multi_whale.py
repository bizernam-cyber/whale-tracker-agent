"""Example: Monitor multiple whales with custom config."""

import asyncio
from whale_tracker.agent import WhaleTracker
from whale_tracker.config import TrackerConfig


async def main():
    # Custom config — lower thresholds
    config = TrackerConfig(
        detection={
            "min_amount_usd": 50000,
            "poll_interval": 6,
            "patterns": {
                "accumulation": {"threshold_pct": 3.0, "window_hours": 12.0},
                "dump": {"threshold_pct": 5.0, "window_hours": 3.0},
            },
        }
    )

    tracker = WhaleTracker(config)

    # Track multiple whales
    whales = [
        ("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "ethereum", "Vitalik"),
        ("0x28C6c06298d514Db089934071355E5743bf21d60", "ethereum", "Binance Hot"),
        ("0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549", "ethereum", "Binance Cold"),
    ]

    for addr, chain, label in whales:
        await tracker.watch(addr, chain, label)

    print(f"Tracking {len(tracker.list_tracked())} whales")

    # Scan each
    for addr, chain, label in whales:
        result = await tracker.scan(addr, chain, days=3)
        print(f"\n{label}: {result['transaction_count']} txs, {len(result['patterns'])} patterns")


if __name__ == "__main__":
    asyncio.run(main())
