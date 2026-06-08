# 🐋 Whale Tracker Agent

Autonomous AI agent that monitors whale wallet movements across multiple blockchains, detects patterns, generates trading theses, and delivers real-time alerts.

## Features

- **Multi-Chain Monitoring** — Ethereum, BSC, Solana, Base, Arbitrum
- **Pattern Detection** — Accumulation, dump, bridge, large transfer, token rotation
- **Real-Time Alerts** — Telegram bot, Discord webhook, terminal dashboard
- **LLM Analysis** — Auto-generate thesis for each whale movement
- **Portfolio Tracking** — Track whale holdings, PnL, token allocation
- **Smart Filtering** — Ignore noise, only alert on significant movements

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                 Whale Tracker Agent                   │
├────────────┬──────────────┬──────────────┬───────────┤
│ Chain      │ Detection    │ Alerts       │ Analysis  │
│ Scanners   │ Engine       │ System       │ Engine    │
│            │              │              │           │
│ • EVM      │ • Threshold  │ • Telegram   │ • LLM     │
│ • Solana   │ • Pattern    │ • Discord    │ • Thesis  │
│ • Indexers │ • Frequency  │ • Terminal   │ • Scoring │
└────────────┴──────────────┴──────────────┴───────────┘
         │           │
    ┌────┴─────┐ ┌───┴───┐
    │ RPC Nodes│ │SQLite │ (state)
    └──────────┘ └───────┘
```

## Quick Start

```bash
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your RPC endpoints and alert tokens

# Track a whale
whale-track watch 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Scan recent activity
whale-track scan 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth --days 7

# Monitor mode (real-time)
whale-track monitor --chain eth --min-amount 100

# List tracked whales
whale-track list
```

## Configuration

```yaml
# config.yaml
chains:
  ethereum:
    rpc: ${ETH_RPC_URL}
    explorer_api: ${ETHERSCAN_API_KEY}
    enabled: true
  bsc:
    rpc: ${BSC_RPC_URL}
    explorer_api: ${BSCSCAN_API_KEY}
    enabled: true
  solana:
    rpc: ${SOLANA_RPC_URL}
    enabled: true

alerts:
  telegram:
    bot_token: ${TELEGRAM_BOT_TOKEN}
    chat_id: ${TELEGRAM_CHAT_ID}
  discord:
    webhook_url: ${DISCORD_WEBHOOK_URL}
  terminal:
    enabled: true

detection:
  min_amount_usd: 100000
  patterns:
    accumulation:
      threshold_pct: 5
      window_hours: 24
    dump:
      threshold_pct: 10
      window_hours: 6
    large_transfer:
      min_amount_usd: 500000

llm:
  provider: openai
  model: gpt-4o
```

## Detection Patterns

| Pattern | Trigger | Description |
|---------|---------|-------------|
| Accumulation | +5% holdings in 24h | Whale buying aggressively |
| Dump | -10% holdings in 6h | Whale selling |
| Large Transfer | >$500K single tx | Significant capital movement |
| Bridge | Cross-chain transfer | Asset moving between chains |
| Token Rotation | Sell A → Buy B | Portfolio rebalancing |
| DEX Activity | Swap on DEX | Direct market impact |

## License

MIT
