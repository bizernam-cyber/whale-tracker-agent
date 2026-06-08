"""CLI interface for Whale Tracker Agent."""

from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from whale_tracker.agent import WhaleTracker
from whale_tracker.config import get_config

app = typer.Typer(
    name="whale-track",
    help="🐋 Autonomous AI agent for whale wallet monitoring",
    add_completion=False,
)
console = Console()


@app.command()
def watch(
    address: str = typer.Argument(help="Wallet address to watch"),
    chain: str = typer.Option("ethereum", "--chain", "-c", help="Blockchain (ethereum, bsc, base, arbitrum)"),
    label: str = typer.Option("", "--label", "-l", help="Label for the wallet"),
    config_path: Optional[str] = typer.Option(None, "--config", help="Path to config.yaml"),
):
    """Add a whale wallet to watch list."""
    config = get_config(config_path)
    tracker = WhaleTracker(config)

    asyncio.run(tracker.watch(address, chain, label))
    console.print(f"[green]✅ Now watching {label or address} on {chain}[/]")


@app.command()
def scan(
    address: str = typer.Argument(help="Wallet address to scan"),
    chain: str = typer.Option("ethereum", "--chain", "-c", help="Blockchain"),
    days: int = typer.Option(7, "--days", "-d", help="Days to scan"),
    config_path: Optional[str] = typer.Option(None, "--config", help="Path to config.yaml"),
):
    """Scan recent whale activity."""
    config = get_config(config_path)
    tracker = WhaleTracker(config)

    console.print(f"[cyan]🔍 Scanning {address} on {chain} ({days}d)...[/]")
    result = asyncio.run(tracker.scan(address, chain, days))

    # Display results
    console.print(f"\n[bold]📊 Scan Results[/]")
    console.print(f"  Transactions: {result['transaction_count']}")

    if result["patterns"]:
        console.print(f"\n[bold]🎯 Detected Patterns:[/]")
        for p in result["patterns"]:
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡"}.get(p.get("severity"), "🟢")
            console.print(f"  {icon} [{p['type']}] {p['description']}")

    if result["analysis"]:
        console.print(f"\n[bold]🧠 Analysis:[/]")
        console.print(result["analysis"])


@app.command()
def monitor(
    chain: str = typer.Option("ethereum", "--chain", "-c", help="Blockchain to monitor"),
    min_amount: float = typer.Option(100, "--min-amount", "-m", help="Min amount in ETH"),
    config_path: Optional[str] = typer.Option(None, "--config", help="Path to config.yaml"),
):
    """Start real-time monitoring."""
    config = get_config(config_path)
    config.detection.min_amount_usd = min_amount * 3000  # Rough ETH price
    tracker = WhaleTracker(config)

    console.print(f"[bold cyan]🐋 Starting whale monitor on {chain}[/]")
    console.print(f"[dim]Min amount: {min_amount} ETH (${config.detection.min_amount_usd:,.0f})[/]")
    console.print("[dim]Press Ctrl+C to stop[/]\n")

    try:
        asyncio.run(tracker.monitor())
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor stopped.[/]")


@app.command()
def balance(
    address: str = typer.Argument(help="Wallet address"),
    chain: str = typer.Option("ethereum", "--chain", "-c", help="Blockchain"),
    config_path: Optional[str] = typer.Option(None, "--config", help="Path to config.yaml"),
):
    """Get wallet balance."""
    config = get_config(config_path)
    tracker = WhaleTracker(config)

    result = asyncio.run(tracker.get_balance(address, chain))

    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/]")
    else:
        console.print(f"[green]{result['balance']:.4f} {result['symbol']}[/]")


@app.command()
def list_wallets(
    config_path: Optional[str] = typer.Option(None, "--config", help="Path to config.yaml"),
):
    """List all tracked wallets."""
    config = get_config(config_path)
    tracker = WhaleTracker(config)

    wallets = tracker.list_tracked()

    if not wallets:
        console.print("[yellow]No wallets tracked. Use 'whale-track watch' to add.[/]")
        return

    table = Table(title="🐋 Tracked Whales")
    table.add_column("Label", style="cyan")
    table.add_column("Address", style="dim")
    table.add_column("Chain", style="green")
    table.add_column("Added", style="dim")

    for w in wallets:
        table.add_row(
            w.get("label", ""),
            w["address"][:10] + "...",
            w.get("chain", ""),
            str(w.get("added_at", "")),
        )

    console.print(table)


@app.command()
def version():
    """Show version."""
    from whale_tracker import __version__
    console.print(f"whale-tracker-agent v{__version__}")


if __name__ == "__main__":
    app()
