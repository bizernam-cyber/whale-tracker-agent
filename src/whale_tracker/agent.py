"""Core whale tracker agent — orchestrates scanning, detection, and alerts."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from whale_tracker.config import TrackerConfig, get_config
from whale_tracker.chains import ChainScanner
from whale_tracker.detectors import DetectionEngine
from whale_tracker.alerts import AlertManager
from whale_tracker.utils.logging import get_logger

logger = get_logger("agent")

THESIS_PROMPT = """You are a crypto whale analyst. Analyze the following whale movement
and generate a concise trading thesis.

Format:
- What happened (1-2 sentences)
- Why it matters (bullish/bearish/neutral)
- Potential impact on price
- Confidence level (1-10)

Be concise, data-driven, and actionable. No fluff.
"""


class WhaleTracker:
    """Main whale tracking agent."""

    def __init__(self, config: Optional[TrackerConfig] = None):
        self.config = config or get_config()
        self.scanner = ChainScanner(self.config)
        self.detector = DetectionEngine(self.config)
        self.alerts = AlertManager(self.config)
        self.llm = self._init_llm()
        self._tracked_wallets: dict[str, dict] = {}
        self._running = False

    def _init_llm(self) -> Optional[ChatOpenAI]:
        """Initialize LLM if API key available."""
        try:
            api_key = self.config.llm.get_api_key()
            return ChatOpenAI(
                model=self.config.llm.model,
                temperature=self.config.llm.temperature,
                api_key=api_key,
            )
        except ValueError:
            logger.warning("No LLM API key — analysis disabled")
            return None

    async def watch(self, address: str, chain: str = "ethereum", label: str = ""):
        """
        Add a whale wallet to watch list.

        Args:
            address: Wallet address
            chain: Blockchain name
            label: Optional label for the wallet
        """
        self._tracked_wallets[address.lower()] = {
            "address": address,
            "chain": chain,
            "label": label or address[:10] + "...",
            "added_at": time.time(),
            "last_scan": None,
        }
        logger.info(f"Watching {label or address} on {chain}")

    async def unwatch(self, address: str):
        """Remove a wallet from watch list."""
        self._tracked_wallets.pop(address.lower(), None)
        logger.info(f"Stopped watching {address}")

    async def scan(self, address: str, chain: str = "ethereum", days: int = 7) -> dict[str, Any]:
        """
        Scan recent activity for a wallet.

        Args:
            address: Wallet address
            chain: Blockchain name
            days: Number of days to scan

        Returns:
            Scan results with transactions, patterns, and analysis.
        """
        logger.info(f"Scanning {address} on {chain} ({days}d)")

        # Fetch transactions
        transactions = await self.scanner.get_transactions(address, chain, days)

        # Detect patterns
        patterns = self.detector.detect(address, transactions)

        # Generate analysis
        analysis = None
        if self.llm and patterns:
            analysis = await self._generate_analysis(address, transactions, patterns)

        return {
            "address": address,
            "chain": chain,
            "days": days,
            "transaction_count": len(transactions),
            "transactions": transactions,
            "patterns": patterns,
            "analysis": analysis,
        }

    async def monitor(self):
        """
        Start real-time monitoring of all tracked wallets.
        Runs until stopped.
        """
        self._running = True
        logger.info(f"Starting monitor — {len(self._tracked_wallets)} wallets tracked")

        while self._running:
            try:
                for address, wallet in list(self._tracked_wallets.items()):
                    chain = wallet["chain"]
                    recent = await self.scanner.get_recent(address, chain)

                    if recent:
                        patterns = self.detector.detect(address, recent)
                        if patterns:
                            # Generate analysis
                            analysis = None
                            if self.llm:
                                analysis = await self._generate_analysis(
                                    address, recent, patterns
                                )

                            # Send alerts
                            await self.alerts.send(
                                wallet=wallet,
                                transactions=recent,
                                patterns=patterns,
                                analysis=analysis,
                            )

                    wallet["last_scan"] = time.time()

                await asyncio.sleep(self.config.detection.poll_interval)

            except KeyboardInterrupt:
                logger.info("Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(5)

        self._running = False

    async def stop(self):
        """Stop monitoring."""
        self._running = False

    async def get_balance(self, address: str, chain: str = "ethereum") -> dict[str, Any]:
        """Get current balance for a wallet."""
        return await self.scanner.get_balance(address, chain)

    async def get_portfolio(self, address: str, chain: str = "ethereum") -> dict[str, Any]:
        """Get full portfolio for a wallet."""
        return await self.scanner.get_portfolio(address, chain)

    def list_tracked(self) -> list[dict]:
        """List all tracked wallets."""
        return list(self._tracked_wallets.values())

    async def _generate_analysis(
        self, address: str, transactions: list, patterns: list
    ) -> Optional[str]:
        """Generate LLM analysis of whale movement."""
        if not self.llm:
            return None

        tx_summary = "\n".join(
            f"- {tx.get('type', 'transfer')}: ${tx.get('amount_usd', 0):,.0f} "
            f"({tx.get('token', 'ETH')}) at {tx.get('timestamp', 'unknown')}"
            for tx in transactions[:10]
        )

        pattern_summary = "\n".join(
            f"- {p['type']}: {p.get('description', '')}" for p in patterns
        )

        prompt = f"""Whale: {address}
Chain: {transactions[0].get('chain', 'unknown') if transactions else 'unknown'}

Recent Transactions:
{tx_summary}

Detected Patterns:
{pattern_summary}

Generate a concise trading thesis."""

        messages = [
            SystemMessage(content=THESIS_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return None
