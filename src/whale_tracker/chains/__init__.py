"""Chain scanners — multi-chain blockchain data fetching."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from whale_tracker.config import TrackerConfig
from whale_tracker.chains.evm import EVMScanner
from whale_tracker.utils.logging import get_logger

logger = get_logger("chains")


class ChainScanner:
    """Orchestrates chain-specific scanners."""

    def __init__(self, config: TrackerConfig):
        self.config = config
        self._scanners: dict[str, EVMScanner] = {}
        self._init_scanners()

    def _init_scanners(self):
        """Initialize enabled chain scanners."""
        for chain_name, chain_config in self.config.chains.items():
            if chain_config.enabled:
                rpc = chain_config.get_rpc()
                if rpc:
                    self._scanners[chain_name] = EVMScanner(
                        chain=chain_name,
                        rpc_url=rpc,
                        explorer_api=chain_config.explorer_api,
                    )
                    logger.info(f"Initialized {chain_name} scanner")

    async def get_transactions(
        self, address: str, chain: str, days: int = 7
    ) -> list[dict[str, Any]]:
        """
        Get transactions for a wallet.

        Args:
            address: Wallet address
            chain: Blockchain name
            days: Number of days to look back

        Returns:
            List of transaction dicts.
        """
        scanner = self._scanners.get(chain)
        if not scanner:
            logger.warning(f"No scanner for chain: {chain}")
            return []
        return await scanner.get_transactions(address, days)

    async def get_recent(self, address: str, chain: str) -> list[dict[str, Any]]:
        """Get recent transactions (since last scan)."""
        scanner = self._scanners.get(chain)
        if not scanner:
            return []
        return await scanner.get_recent(address)

    async def get_balance(self, address: str, chain: str) -> dict[str, Any]:
        """Get native token balance."""
        scanner = self._scanners.get(chain)
        if not scanner:
            return {"error": f"No scanner for {chain}"}
        return await scanner.get_balance(address)

    async def get_portfolio(self, address: str, chain: str) -> dict[str, Any]:
        """Get full portfolio (native + tokens)."""
        scanner = self._scanners.get(chain)
        if not scanner:
            return {"error": f"No scanner for {chain}"}
        return await scanner.get_portfolio(address)

    def get_enabled_chains(self) -> list[str]:
        """Get list of enabled chain names."""
        return list(self._scanners.keys())
