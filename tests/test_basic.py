"""Tests for Whale Tracker Agent."""

import pytest
from whale_tracker.config import TrackerConfig, ChainConfig, PatternConfig
from whale_tracker.detectors.patterns import (
    detect_accumulation,
    detect_dump,
    detect_large_transfer,
    detect_rotation,
    detect_bridge,
)
from whale_tracker.utils import shorten_address, wei_to_eth, eth_to_usd, RateLimiter


class TestConfig:
    """Tests for configuration."""

    def test_default_config(self):
        config = TrackerConfig()
        assert "ethereum" in config.chains
        assert config.detection.min_amount_usd == 100000.0
        assert config.llm.model == "gpt-4o"

    def test_chain_config(self):
        chain = ChainConfig(rpc="https://example.com", enabled=True)
        assert chain.get_rpc() == "https://example.com"
        assert chain.enabled is True

    def test_config_load_missing(self):
        config = TrackerConfig.load("/nonexistent/path.yaml")
        assert "ethereum" in config.chains


class TestPatterns:
    """Tests for pattern detection."""

    def _make_tx(self, tx_type: str, value: float, token: str = "ETH", timestamp: float = 0):
        return {
            "hash": "0xabc",
            "from": "0x123" if tx_type == "send" else "0x456",
            "to": "0x456" if tx_type == "send" else "0x123",
            "value": value,
            "token": token,
            "type": tx_type,
            "block": 1000,
            "timestamp": timestamp or __import__("time").time(),
            "chain": "ethereum",
        }

    def test_detect_accumulation(self):
        import time
        now = time.time()
        txs = [
            self._make_tx("receive", 100, timestamp=now - 3600),
            self._make_tx("receive", 200, timestamp=now - 1800),
            self._make_tx("send", 10, timestamp=now - 900),
        ]

        config = PatternConfig(threshold_pct=5.0, window_hours=24.0, min_amount_usd=100000)
        result = detect_accumulation("0x456", txs, config)

        assert result is not None
        assert result["type"] == "accumulation"
        assert result["inflow"] == 300

    def test_detect_dump(self):
        import time
        now = time.time()
        txs = [
            self._make_tx("send", 500, timestamp=now - 3600),
            self._make_tx("send", 300, timestamp=now - 1800),
        ]

        config = PatternConfig(threshold_pct=10.0, window_hours=6.0, min_amount_usd=100000)
        result = detect_dump("0x123", txs, config)

        assert result is not None
        assert result["type"] == "dump"
        assert result["outflow"] == 800

    def test_detect_large_transfer(self):
        txs = [self._make_tx("send", 200)]

        config = PatternConfig(min_amount_usd=500000)
        result = detect_large_transfer("0x123", txs, config)

        assert result is not None
        assert result["type"] == "large_transfer"

    def test_detect_large_transfer_none(self):
        txs = [self._make_tx("send", 0.1)]

        config = PatternConfig(min_amount_usd=500000)
        result = detect_large_transfer("0x123", txs, config)

        assert result is None

    def test_detect_rotation(self):
        txs = [
            self._make_tx("send", 10, token="USDC"),
            self._make_tx("receive", 5, token="WBTC"),
        ]

        result = detect_rotation("0x123", txs)

        assert result is not None
        assert result["type"] == "rotation"
        assert "USDC" in result["sold"]
        assert "WBTC" in result["bought"]

    def test_detect_bridge(self):
        txs = [{
            "hash": "0xabc",
            "from": "0x123",
            "to": "0x3154cf16ccdb4c6d922629664174b904d80f2c35",
            "value": 10,
            "token": "ETH",
            "type": "send",
            "block": 1000,
            "timestamp": 0,
            "chain": "ethereum",
        }]

        result = detect_bridge("0x123", txs)

        assert result is not None
        assert result["type"] == "bridge"
        assert result["bridge"] == "LayerZero"

    def test_no_patterns_empty(self):
        patterns = detect_accumulation("0x123", [], None)
        assert patterns is None


class TestUtils:
    """Tests for utility functions."""

    def test_shorten_address(self):
        addr = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        assert shorten_address(addr) == "0xd8dA6B...A96045"

    def test_wei_to_eth(self):
        assert wei_to_eth(1e18) == 1.0
        assert wei_to_eth(5e17) == 0.5

    def test_eth_to_usd(self):
        assert eth_to_usd(1.0, 3000) == 3000.0
        assert eth_to_usd(2.5, 2000) == 5000.0

    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        import time
        limiter = RateLimiter(calls_per_second=10)
        start = time.monotonic()
        await limiter.wait()
        await limiter.wait()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.09  # ~100ms between calls
