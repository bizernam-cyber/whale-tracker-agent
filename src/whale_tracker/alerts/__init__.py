"""Alert system — Telegram, Discord, and terminal notifications."""

from __future__ import annotations

from typing import Any, Optional

import aiohttp

from whale_tracker.config import TrackerConfig
from whale_tracker.utils.logging import get_logger

logger = get_logger("alerts")


class AlertManager:
    """Manages alert delivery across multiple channels."""

    def __init__(self, config: TrackerConfig):
        self.config = config

    async def send(
        self,
        wallet: dict,
        transactions: list[dict],
        patterns: list[dict],
        analysis: Optional[str] = None,
    ):
        """
        Send alerts to all enabled channels.

        Args:
            wallet: Wallet metadata (address, label, chain)
            transactions: Recent transactions
            patterns: Detected patterns
            analysis: Optional LLM analysis
        """
        message = self._format_message(wallet, transactions, patterns, analysis)

        # Terminal (always)
        if self.config.alerts.terminal.enabled:
            self._send_terminal(message, patterns)

        # Telegram
        if self.config.alerts.telegram.bot_token and self.config.alerts.telegram.chat_id:
            await self._send_telegram(message)

        # Discord
        if self.config.alerts.discord.webhook_url:
            await self._send_discord(wallet, patterns, analysis)

    def _format_message(
        self,
        wallet: dict,
        transactions: list[dict],
        patterns: list[dict],
        analysis: Optional[str],
    ) -> str:
        """Format alert message."""
        lines = [
            f"🐋 WHALE ALERT — {wallet.get('label', 'Unknown')}",
            f"Chain: {wallet.get('chain', 'unknown').upper()}",
            f"Address: {wallet['address'][:8]}...{wallet['address'][-6:]}",
            "",
        ]

        # Patterns
        for p in patterns:
            severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                p.get("severity", "medium"), "⚪"
            )
            lines.append(f"{severity_icon} [{p['type'].upper()}] {p['description']}")

        lines.append("")

        # Recent transactions
        if transactions:
            lines.append(f"📊 Recent Activity ({len(transactions)} txs):")
            for tx in transactions[:5]:
                arrow = "→" if tx.get("type") == "send" else "←"
                lines.append(
                    f"  {arrow} {tx.get('value', 0):.4f} {tx.get('token', 'ETH')} "
                    f"({tx.get('type', 'unknown')})"
                )

        # Analysis
        if analysis:
            lines.extend(["", "🧠 Analysis:", analysis])

        return "\n".join(lines)

    def _send_terminal(self, message: str, patterns: list[dict]):
        """Print alert to terminal."""
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        severity = "bold red" if any(p.get("severity") == "critical" for p in patterns) else "bold cyan"
        console.print(Panel(message, title="🐋 Whale Alert", border_style=severity))

    async def _send_telegram(self, message: str):
        """Send alert via Telegram bot."""
        token = self.config.alerts.telegram.bot_token
        chat_id = self.config.alerts.telegram.chat_id

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message[:4000],  # Telegram limit
            "parse_mode": "Markdown",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        logger.error(f"Telegram alert failed: {resp.status}")
                    else:
                        logger.debug("Telegram alert sent")
        except Exception as e:
            logger.error(f"Telegram alert error: {e}")

    async def _send_discord(
        self, wallet: dict, patterns: list[dict], analysis: Optional[str]
    ):
        """Send alert via Discord webhook."""
        webhook_url = self.config.alerts.discord.webhook_url

        # Build Discord embed
        embed = {
            "title": f"🐋 Whale Alert — {wallet.get('label', 'Unknown')}",
            "color": 0xFF0000 if any(p.get("severity") == "critical" for p in patterns) else 0x00AAFF,
            "fields": [],
        }

        for p in patterns:
            embed["fields"].append({
                "name": f"[{p['type'].upper()}]",
                "value": p["description"],
                "inline": False,
            })

        if analysis:
            embed["fields"].append({
                "name": "🧠 Analysis",
                "value": analysis[:1024],
                "inline": False,
            })

        embed["footer"] = {"text": f"Chain: {wallet.get('chain', 'unknown').upper()}"}

        payload = {"embeds": [embed]}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status not in (200, 204):
                        logger.error(f"Discord alert failed: {resp.status}")
                    else:
                        logger.debug("Discord alert sent")
        except Exception as e:
            logger.error(f"Discord alert error: {e}")
