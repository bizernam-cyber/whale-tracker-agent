"""Pattern detection functions."""

from __future__ import annotations

import time
from typing import Any, Optional

from whale_tracker.config import PatternConfig


def detect_accumulation(
    address: str,
    transactions: list[dict],
    config: Optional[PatternConfig] = None,
) -> Optional[dict[str, Any]]:
    """
    Detect accumulation pattern — whale buying aggressively.

    Trigger: Net inflow exceeds threshold % of recent holdings.
    """
    if not config:
        config = PatternConfig(threshold_pct=5.0, window_hours=24.0)

    cutoff = time.time() - (config.window_hours * 3600)
    recent = [tx for tx in transactions if tx.get("timestamp", 0) > cutoff]

    if not recent:
        return None

    # Calculate net flow
    inflow = sum(tx["value"] for tx in recent if tx.get("type") == "receive")
    outflow = sum(tx["value"] for tx in recent if tx.get("type") == "send")
    net = inflow - outflow

    # If significant net inflow
    if net > 0 and inflow > config.min_amount_usd / 3000:  # Rough ETH price
        return {
            "type": "accumulation",
            "severity": "high" if net > config.min_amount_usd / 1000 else "medium",
            "description": f"Net accumulation of {net:.2f} ETH over {config.window_hours}h",
            "net_flow": net,
            "inflow": inflow,
            "outflow": outflow,
            "tx_count": len(recent),
            "window_hours": config.window_hours,
        }

    return None


def detect_dump(
    address: str,
    transactions: list[dict],
    config: Optional[PatternConfig] = None,
) -> Optional[dict[str, Any]]:
    """
    Detect dump pattern — whale selling aggressively.

    Trigger: Net outflow exceeds threshold % of holdings.
    """
    if not config:
        config = PatternConfig(threshold_pct=10.0, window_hours=6.0)

    cutoff = time.time() - (config.window_hours * 3600)
    recent = [tx for tx in transactions if tx.get("timestamp", 0) > cutoff]

    if not recent:
        return None

    inflow = sum(tx["value"] for tx in recent if tx.get("type") == "receive")
    outflow = sum(tx["value"] for tx in recent if tx.get("type") == "send")
    net = outflow - inflow

    if net > 0 and outflow > config.min_amount_usd / 3000:
        return {
            "type": "dump",
            "severity": "critical" if net > config.min_amount_usd / 500 else "high",
            "description": f"Net outflow of {net:.2f} ETH over {config.window_hours}h",
            "net_flow": -net,
            "inflow": inflow,
            "outflow": outflow,
            "tx_count": len(recent),
            "window_hours": config.window_hours,
        }

    return None


def detect_large_transfer(
    address: str,
    transactions: list[dict],
    config: Optional[PatternConfig] = None,
) -> Optional[dict[str, Any]]:
    """
    Detect large single transfer.

    Trigger: Single transaction exceeds min_amount_usd.
    """
    if not config:
        config = PatternConfig(min_amount_usd=500000.0)

    threshold_eth = config.min_amount_usd / 3000  # Rough price

    large = [
        tx for tx in transactions
        if tx.get("value", 0) >= threshold_eth
    ]

    if large:
        biggest = max(large, key=lambda x: x.get("value", 0))
        return {
            "type": "large_transfer",
            "severity": "high",
            "description": f"Transfer of {biggest['value']:.2f} ETH (${biggest['value'] * 3000:,.0f})",
            "tx_hash": biggest.get("hash"),
            "from": biggest.get("from"),
            "to": biggest.get("to"),
            "value": biggest.get("value"),
            "direction": biggest.get("type"),
        }

    return None


def detect_rotation(address: str, transactions: list[dict]) -> Optional[dict[str, Any]]:
    """
    Detect token rotation pattern — selling one token, buying another.

    Trigger: Outflow in one token coincides with inflow in another.
    """
    recent = transactions[:50]  # Check last 50 txs

    sends = [tx for tx in recent if tx.get("type") == "send" and tx.get("token") != "ETH"]
    receives = [tx for tx in recent if tx.get("type") == "receive" and tx.get("token") != "ETH"]

    if sends and receives:
        sent_tokens = set(tx.get("token") for tx in sends)
        received_tokens = set(tx.get("token") for tx in receives)

        # If selling A and buying B
        if sent_tokens and received_tokens and not sent_tokens.intersection(received_tokens):
            return {
                "type": "rotation",
                "severity": "medium",
                "description": f"Rotating from {sent_tokens} to {received_tokens}",
                "sold": list(sent_tokens),
                "bought": list(received_tokens),
            }

    return None


def detect_bridge(address: str, transactions: list[dict]) -> Optional[dict[str, Any]]:
    """
    Detect bridge activity — sending to known bridge contracts.

    Trigger: Transfer to/from known bridge addresses.
    """
    # Known bridge addresses (simplified)
    bridges = {
        "0x3154cf16ccdb4c6d922629664174b904d80f2c35": "LayerZero",
        "0x99c9fc46f92e8a1c0dec1b1747d010903e884be1": "Optimism Bridge",
        "0x4dbd4fc535ac27206064b68ffcf827b0a60bab3f": "Arbitrum Bridge",
        "0xa0c68c638235ee32657e8f720a23cec1bfc77c77": "Polygon Bridge",
        "0x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf": "Polygon Bridge (PoS)",
    }

    for tx in transactions:
        to = tx.get("to", "").lower()
        if to in bridges:
            return {
                "type": "bridge",
                "severity": "medium",
                "description": f"Bridging via {bridges[to]}",
                "bridge": bridges[to],
                "tx_hash": tx.get("hash"),
                "value": tx.get("value"),
                "direction": tx.get("type"),
            }

    return None
