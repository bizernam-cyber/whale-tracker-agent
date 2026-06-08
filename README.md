# 🐋 Whale Tracker Agent

> AI agent that monitors whale wallets across 4 blockchains, detects patterns in real-time, and alerts you before the market moves.

## What it does

```
Wallet Activity → Pattern Detection → AI Analysis → Alerts
     (ETH/BSC/         (5 types)        (thesis)    (TG/Discord)
      Base/Arb)
```

**Detected Patterns:**
- 🟠 **Accumulation** — Whale buying aggressively (+5% in 24h)
- 🔴 **Dump** — Whale selling (-10% in 6h)
- 🟡 **Large Transfer** — Single tx > $500K
- 🟡 **Token Rotation** — Selling A → Buying B
- 🟡 **Bridge** — Cross-chain via LayerZero, Arbitrum Bridge, etc.

## Install

```bash
git clone https://github.com/bizernam-cyber/whale-tracker-agent
cd whale-tracker-agent
pip install -e .

# Set RPC
export ETH_RPC_URL="https://eth.llamarpc.com"
```

## Usage

```bash
# Watch a whale
whale-track watch 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --label "Vitalik"

# Scan 7 days of activity
whale-track scan 0xd8dA...6045 --chain eth --days 7

# Real-time monitor (alerts on movements > 100 ETH)
whale-track monitor --chain eth --min-amount 100

# Check balance
whale-track balance 0xd8dA...6045
```

## Python API

```python
import asyncio
from whale_tracker.agent import WhaleTracker

async def main():
    tracker = WhaleTracker()

    # Track
    await tracker.watch("0xd8dA...6045", chain="ethereum", label="Vitalik")

    # Scan
    result = await tracker.scan("0xd8dA...6045", days=7)
    print(f"Transactions: {result['transaction_count']}")
    print(f"Patterns: {[p['type'] for p in result['patterns']]}")

    # Monitor (real-time)
    await tracker.monitor()

asyncio.run(main())
```

## Alerts

| Channel | Setup |
|---------|-------|
| Terminal | Default — Rich panels, no config needed |
| Telegram | Set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` in .env |
| Discord | Set `DISCORD_WEBHOOK_URL` in .env |

## Supported Chains

| Chain | Status |
|-------|--------|
| Ethereum | ✅ Full support |
| BNB Chain | ✅ Full support |
| Base | ✅ Full support |
| Arbitrum | ✅ Full support |

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Whale Tracker Agent                 │
├───────────┬─────────────┬───────────┬───────────┤
│  Chain    │  Detection  │  Alerts   │  Analysis │
│  Scanners │  Engine     │  System   │  Engine   │
│           │             │           │           │
│  EVM      │  Threshold  │  Telegram │  LLM      │
│  (4 chains│  Pattern    │  Discord  │  Thesis   │
│  unified) │  Frequency  │  Terminal │  Scoring  │
└───────────┴─────────────┴───────────┴───────────┘
```

## License

MIT
