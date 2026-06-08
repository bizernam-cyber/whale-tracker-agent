"""Pattern detection engine."""

from __future__ import annotations

import time
from typing import Any

from whale_tracker.config import TrackerConfig
from whale_tracker.detectors.patterns import (
    detect_accumulation,
    detect_dump,
    detect_large_transfer,
    detect_rotation,
    detect_bridge,
)
from whale_tracker.utils.logging import get_logger

logger = get_logger("detectors")


class DetectionEngine:
    """Runs pattern detection on transaction data."""

    def __init__(self, config: TrackerConfig):
        self.config = config
        self.min_amount = config.detection.min_amount_usd

    def detect(self, address: str, transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Detect patterns in transactions.

        Args:
            address: Wallet address
            transactions: List of transaction dicts

        Returns:
            List of detected pattern dicts.
        """
        if not transactions:
            return []

        patterns = []

        # Accumulation
        result = detect_accumulation(
            address, transactions,
            self.config.detection.patterns.get("accumulation"),
        )
        if result:
            patterns.append(result)

        # Dump
        result = detect_dump(
            address, transactions,
            self.config.detection.patterns.get("dump"),
        )
        if result:
            patterns.append(result)

        # Large Transfer
        result = detect_large_transfer(
            address, transactions,
            self.config.detection.patterns.get("large_transfer"),
        )
        if result:
            patterns.append(result)

        # Token Rotation
        result = detect_rotation(address, transactions)
        if result:
            patterns.append(result)

        # Bridge
        result = detect_bridge(address, transactions)
        if result:
            patterns.append(result)

        return patterns
