"""EVM chain scanner — Ethereum, BSC, Base, Arbitrum, etc."""

from __future__ import annotations

import time
from typing import Any, Optional

import aiohttp
from web3 import Web3

from whale_tracker.utils.logging import get_logger

logger = get_logger("evm")

# ERC-20 Transfer event signature
ERC20_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


class EVMScanner:
    """EVM-compatible chain scanner."""

    def __init__(self, chain: str, rpc_url: str, explorer_api: Optional[str] = None):
        self.chain = chain
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.explorer_api = explorer_api
        self._last_block: dict[str, int] = {}

    async def get_transactions(self, address: str, days: int = 7) -> list[dict[str, Any]]:
        """
        Get transactions for an address using RPC + logs.

        Args:
            address: Wallet address
            days: Number of days to look back

        Returns:
            List of transaction dicts.
        """
        try:
            current_block = self.w3.eth.block_number
            blocks_per_day = 86400 / 12  # ~7200 blocks/day on ETH
            from_block = max(0, int(current_block - (days * blocks_per_day)))

            # Get native transfers via balance changes
            txs = await self._get_native_transfers(address, from_block, current_block)

            # Get ERC-20 transfers via logs
            erc20_txs = await self._get_erc20_transfers(address, from_block, current_block)
            txs.extend(erc20_txs)

            # Sort by block number
            txs.sort(key=lambda x: x.get("block", 0), reverse=True)

            return txs

        except Exception as e:
            logger.error(f"Failed to get transactions for {address}: {e}")
            return []

    async def get_recent(self, address: str) -> list[dict[str, Any]]:
        """Get transactions since last scan."""
        last_block = self._last_block.get(address.lower(), 0)
        if last_block == 0:
            # First scan — get last 100 blocks
            current = self.w3.eth.block_number
            last_block = max(0, current - 100)

        current_block = self.w3.eth.block_number
        if current_block <= last_block:
            return []

        txs = await self._get_native_transfers(address, last_block, current_block)
        erc20_txs = await self._get_erc20_transfers(address, last_block, current_block)
        txs.extend(erc20_txs)

        self._last_block[address.lower()] = current_block
        return txs

    async def get_balance(self, address: str) -> dict[str, Any]:
        """Get native token balance."""
        try:
            checksum = Web3.to_checksum_address(address)
            balance_wei = self.w3.eth.get_balance(checksum)
            balance_eth = self.w3.from_wei(balance_wei, "ether")

            return {
                "address": address,
                "chain": self.chain,
                "balance": float(balance_eth),
                "balance_wei": balance_wei,
                "symbol": self._get_native_symbol(),
            }
        except Exception as e:
            return {"error": str(e)}

    async def get_portfolio(self, address: str) -> dict[str, Any]:
        """Get full portfolio (native + top tokens)."""
        balance = await self.get_balance(address)
        tokens = await self._get_token_holdings(address)

        return {
            "address": address,
            "chain": self.chain,
            "native": balance,
            "tokens": tokens,
            "total_tokens": len(tokens),
        }

    async def _get_native_transfers(
        self, address: str, from_block: int, to_block: int
    ) -> list[dict[str, Any]]:
        """Get native token transfers by scanning blocks."""
        txs = []
        checksum = Web3.to_checksum_address(address)

        # Scan in chunks to avoid timeout
        chunk_size = 100
        for start in range(from_block, to_block + 1, chunk_size):
            end = min(start + chunk_size - 1, to_block)
            try:
                for block_num in range(start, end + 1):
                    block = self.w3.eth.get_block(block_num, full_transactions=True)
                    for tx in block.transactions:
                        if tx["from"].lower() == checksum.lower() or \
                           (tx.get("to") and tx["to"].lower() == checksum.lower()):
                            value_eth = float(self.w3.from_wei(tx["value"], "ether"))
                            if value_eth > 0:
                                txs.append({
                                    "hash": tx["hash"].hex(),
                                    "from": tx["from"],
                                    "to": tx.get("to", ""),
                                    "value": value_eth,
                                    "value_wei": tx["value"],
                                    "token": self._get_native_symbol(),
                                    "type": "send" if tx["from"].lower() == checksum.lower() else "receive",
                                    "block": block_num,
                                    "timestamp": block.timestamp,
                                    "chain": self.chain,
                                })
            except Exception as e:
                logger.debug(f"Block scan error at {start}: {e}")
                continue

        return txs

    async def _get_erc20_transfers(
        self, address: str, from_block: int, to_block: int
    ) -> list[dict[str, Any]]:
        """Get ERC-20 token transfers via logs."""
        txs = []
        checksum = Web3.to_checksum_address(address)

        # Pad address to 32 bytes
        padded = "0x" + checksum[2:].lower().zfill(64)

        try:
            # Get logs where address is sender
            logs = self.w3.eth.get_logs({
                "fromBlock": from_block,
                "toBlock": to_block,
                "topics": [ERC20_TRANSFER_TOPIC, padded],
            })

            for log in logs:
                txs.append(self._parse_erc20_log(log, checksum, "send"))

            # Get logs where address is receiver
            logs = self.w3.eth.get_logs({
                "fromBlock": from_block,
                "toBlock": to_block,
                "topics": [ERC20_TRANSFER_TOPIC, None, padded],
            })

            for log in logs:
                txs.append(self._parse_erc20_log(log, checksum, "receive"))

        except Exception as e:
            logger.debug(f"ERC-20 log fetch error: {e}")

        return txs

    def _parse_erc20_log(self, log: dict, address: str, direction: str) -> dict[str, Any]:
        """Parse an ERC-20 Transfer log."""
        topics = log["topics"]
        from_addr = "0x" + topics[1].hex()[-40:]
        to_addr = "0x" + topics[2].hex()[-40:]

        # Decode value (assuming 18 decimals for now)
        value_raw = int(log["data"].hex(), 16) if isinstance(log["data"], bytes) else int(log["data"], 16)
        value = value_raw / 1e18

        return {
            "hash": log["transactionHash"].hex() if isinstance(log["transactionHash"], bytes) else log["transactionHash"],
            "from": from_addr,
            "to": to_addr,
            "value": value,
            "token": "ERC20",  # Would need contract call for symbol
            "contract": log["address"],
            "type": direction,
            "block": log["blockNumber"],
            "timestamp": 0,  # Would need block lookup
            "chain": self.chain,
        }

    async def _get_token_holdings(self, address: str) -> list[dict[str, Any]]:
        """Get token holdings (simplified — would need indexing for full portfolio)."""
        # In production, use Etherscan/BSCScan API or index service
        return []

    def _get_native_symbol(self) -> str:
        """Get native token symbol for chain."""
        symbols = {
            "ethereum": "ETH",
            "bsc": "BNB",
            "base": "ETH",
            "arbitrum": "ETH",
            "polygon": "MATIC",
            "avalanche": "AVAX",
        }
        return symbols.get(self.chain, "ETH")
