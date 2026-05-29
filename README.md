# Fortress MCP Server

MCP server connecting Claude to the **Fortress Trading Dashboard V4**.
64 tools across portfolio analysis, IBKR management, options strategy, and QuantData market data.

---

## Installation

### 1. Install dependencies

```bash
pip3 install mcp httpx requests
```

### 2. Copy MCP server to WSL

```bash
mkdir -p /home/ubuntu/fortress_mcp
cp fortress_mcp.py /home/ubuntu/fortress_mcp/
```

### 3. Add to Claude Desktop config

Merge `claude_desktop_config_snippet.json` into your Claude Desktop config at:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **WSL**: `/home/ubuntu/.config/Claude/claude_desktop_config.json`

The snippet is pre-configured for local WSL (http://localhost:8081). Update `FORTRESS_API_TOKEN` to match your dashboard token.

### 4. Restart Claude Desktop

---

## Configuration

| Variable | Description | Default |
|---|---|---|
| `FORTRESS_API_URL` | Dashboard API URL | `http://localhost:8081` |
| `FORTRESS_API_TOKEN` | Bearer token | *(required)* |
| `FORTRESS_MCP_ALLOW_WRITES` | Enable write tools | `0` (read-only) |

---

## Tool Tiers

| Tier | Count | Description |
|---|---|---|
| **Tier 1** | 45 | Read-only: briefing, positions, P&L, alerts, market intelligence, analytics, options |
| **Tier 2** | 10 | Writes (set `FORTRESS_MCP_ALLOW_WRITES=1`): alerts, journal, settings, IBKR sync |
| **QD** | 6 | QuantData live: IV rank, dark pool, order flow, net drift, max pain, OI change |
| **Charts** | 3 | OHLCV candles, GEX/DP levels, order flow overlays |

Key tools: `get_briefing()`, `get_positions()`, `evaluate_stop_loss()`, `evaluate_roll()`, `pretrade_check()`, `get_capability()`, `qd_get_iv_rank()`, `get_pnl_history()`, `get_chart_data()`

---

## Usage with Claude

Always start with `get_briefing()` for any portfolio question — it returns the full situation summary including positions, P&L, regime, and pending actions.

See `examples/` for sample workflows.

---

## Architecture

```
Claude Desktop
    │  stdio
    ▼
fortress_mcp.py  (this file)
    │  HTTP + Bearer token
    ▼
Fortress V4 API  (http://localhost:8081)
    │
    ├── IBKR (ibind OAuth 1.0a or CP Gateway)
    ├── QuantData.us
    └── MySQL + Redis
```

---

## Related Repositories

| Repo | Description |
|---|---|
| [fortress-v4-api](https://github.com/citychip/fortress-v4-api) | FastAPI backend |
| [fortress-v4-frontend](https://github.com/citychip/fortress-v4-frontend) | React frontend |
| [fortress-install](https://github.com/citychip/fortress-install) | WSL installation guide |

---

## Changelog

| Version | Summary |
|---|---|
| v4.1 | 64 tools; default URL → localhost:8081; ibind OAuth support in backend |
| v4.0 | V4 backend integration; QD proxy tools; dual-token auth |
| v3.9 | Dynamic QD tool ID discovery |
| v3.7 | 61 tools; portfolio analytics tier |
