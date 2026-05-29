# Fortress MCP Server

MCP server connecting Claude to the **Fortress Trading Dashboard V4**.
64 tools across portfolio analysis, IBKR management, options strategy, and QuantData market data.

---

## Quick Install (Windows)

1. Download or clone this repo to a folder on your PC (e.g. `C:\Users\you\fortress_mcp\`)

2. Run the installer from PowerShell:
   ```powershell
   cd C:\Users\you\fortress_mcp
   python install_fortress.py
   ```
   This installs dependencies (`mcp`, `httpx`, `requests`) and writes the MCP config to Claude Desktop automatically. It supports both traditional and Microsoft Store (UWP) Claude installs.

3. Edit `claude_desktop_config.json` (path printed by the installer) and set your `FORTRESS_API_TOKEN`.

4. Fully quit Claude from the system tray icon and relaunch.

---

## Manual Install

If you prefer to configure manually, merge `claude_desktop_config_snippet.json` into your Claude Desktop config:

- **Traditional install**: `%APPDATA%\Claude\claude_desktop_config.json`
- **UWP / Store install**: `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json`

---

## Configuration

| Variable | Description | Default |
|---|---|---|
| `FORTRESS_API_URL` | Dashboard API URL | `http://localhost:8081` |
| `FORTRESS_API_TOKEN` | Bearer token | *(set this)* |
| `FORTRESS_MCP_ALLOW_WRITES` | Enable write tools | `1` (enabled) |

---

## Requirements

```bash
pip install mcp httpx requests
```

---

## Tool Tiers — 64 tools total

| Tier | Count | Description |
|---|---|---|
| **Tier 1** | 45 | Read-only: briefing, positions, P&L, alerts, market intelligence, analytics, options |
| **Tier 2** | 10 | Writes (enabled by default): alerts, journal, settings, IBKR sync, scripts, orders |
| **QD** | 6 | QuantData live: IV rank, dark pool, order flow, net drift, max pain, OI change |
| **Charts** | 3 | OHLCV candles, GEX/DP levels, order flow overlays |

Always start with `get_briefing()` — it returns the full portfolio situation summary.

---

## Architecture

```
Claude Desktop (Windows)
    │  stdio
    ▼
fortress_mcp.py  ← runs as Windows Python process
    │  HTTP + Bearer token
    ▼
Fortress V4 API  (http://localhost:8081 — running in WSL)
    │
    ├── IBKR (ibind OAuth 1.0a or CP Gateway at localhost:5000)
    ├── QuantData.us
    └── MySQL + Redis (WSL)
```

---

## Related Repositories

| Repo | Description |
|---|---|
| [fortress-v4-api](https://github.com/citychip/fortress-v4-api) | FastAPI backend |
| [fortress-v4-frontend](https://github.com/citychip/fortress-v4-frontend) | React frontend |
| [fortress-install](https://github.com/citychip/fortress-install) | WSL installation guide and scripts |
