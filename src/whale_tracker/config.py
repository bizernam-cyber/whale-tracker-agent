"""Configuration management for Whale Tracker Agent."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class ChainConfig(BaseModel):
    """Blockchain configuration."""

    rpc: str = ""
    explorer_api: Optional[str] = None
    enabled: bool = True
    block_time: float = 12.0  # seconds
    confirmations: int = 12

    def get_rpc(self) -> str:
        """Resolve RPC URL from env or direct value."""
        if self.rpc.startswith("${"):
            var = self.rpc[2:-1]
            return os.getenv(var, "")
        return self.rpc


class AlertConfig(BaseModel):
    """Alert channel configuration."""

    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    webhook_url: Optional[str] = None
    enabled: bool = True


class AlertsConfig(BaseModel):
    """All alert channels."""

    telegram: AlertConfig = Field(default_factory=AlertConfig)
    discord: AlertConfig = Field(default_factory=AlertConfig)
    terminal: AlertConfig = Field(default_factory=lambda: AlertConfig(enabled=True))


class PatternConfig(BaseModel):
    """Detection pattern configuration."""

    threshold_pct: float = 5.0
    window_hours: float = 24.0
    min_amount_usd: float = 100000.0


class DetectionConfig(BaseModel):
    """Detection engine configuration."""

    min_amount_usd: float = 100000.0
    patterns: dict[str, PatternConfig] = Field(default_factory=lambda: {
        "accumulation": PatternConfig(threshold_pct=5.0, window_hours=24.0),
        "dump": PatternConfig(threshold_pct=10.0, window_hours=6.0),
        "large_transfer": PatternConfig(min_amount_usd=500000.0),
    })
    poll_interval: int = 12  # seconds
    max_blocks_per_scan: int = 100


class LLMConfig(BaseModel):
    """LLM configuration for analysis."""

    provider: str = "openai"
    model: str = "gpt-4o"
    temperature: float = 0.1
    api_key: Optional[str] = None

    def get_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("Missing OPENAI_API_KEY")
        return key


class TrackerConfig(BaseModel):
    """Root configuration."""

    chains: dict[str, ChainConfig] = Field(default_factory=lambda: {
        "ethereum": ChainConfig(
            rpc=os.getenv("ETH_RPC_URL", "https://eth.llamarpc.com"),
            explorer_api=os.getenv("ETHERSCAN_API_KEY"),
            block_time=12.0,
            confirmations=12,
        ),
        "bsc": ChainConfig(
            rpc=os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org/"),
            explorer_api=os.getenv("BSCSCAN_API_KEY"),
            block_time=3.0,
            confirmations=15,
        ),
        "base": ChainConfig(
            rpc=os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
            block_time=2.0,
            confirmations=12,
        ),
        "arbitrum": ChainConfig(
            rpc=os.getenv("ARB_RPC_URL", "https://arb1.arbitrum.io/rpc"),
            block_time=0.25,
            confirmations=12,
        ),
    })
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "TrackerConfig":
        """Load config from YAML file with env var substitution."""
        path = Path(config_path) if config_path else Path("config.yaml")
        if not path.exists():
            return cls()

        with open(path) as f:
            raw = f.read()

        import re
        def _sub(match: re.Match) -> str:
            return os.getenv(match.group(1), match.group(0))

        raw = re.sub(r"\$\{(\w+)\}", _sub, raw)
        data = yaml.safe_load(raw) or {}
        return cls(**data)


def get_config(config_path: Optional[str] = None) -> TrackerConfig:
    """Get configuration."""
    return TrackerConfig.load(config_path)
