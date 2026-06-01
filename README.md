# Fortress MCP Server

MCP server connecting Claude to the Fortress Trading Dashboard V4.
62 tools across portfolio analysis, IBKR management, and options strategy.

> **QuantData** is handled by the standalone `quantdata-mcp` server (registered separately). See setup below.

## Quick Setup (WSL / Local)

1. Copy `fortress_mcp.py` to WSL:
   ```bash
   mkdir -p /home/ubuntu/fortress_mcp
   cp fortress_mcp.py /home/ubuntu/fortress_mcp/
   ```

2. Install dependencies:
   ```bash
   pip3 install mcp httpx requests
   ```

3. Install the QuantData MCP:
   ```bash
   pip3 install quantdata-mcp --break-system-packages
   # Credentials are read from ~/.quantdata-mcp/config.json (already configured)
   ```

4. Add both config blocks to Claude Desktop's `claude_desktop_config.json`:
   - Windows path: `%APPDATA%\Claude\claude_desktop_config.json`
   - Merge the contents of `claude_desktop_config_snippet.json` into it
   - Add the quantdata block:
     ```json
     "quantdata": {
       "command": "wsl",
       "args": ["-e", "/home/ubuntu/.local/bin/quantdata-mcp", "serve"]
     }
     ```

5. Restart Claude Desktop

## Configuration

The `claude_desktop_config_snippet.json` is pre-configured for local WSL use:
- `FORTRESS_API_URL`: `http://localhost:8081`
- `FORTRESS_API_TOKEN`: your bearer token

QuantData credentials are stored in `~/.quantdata-mcp/config.json` on WSL. After a credential refresh, restart Claude Desktop to pick up the updated token.

## Tool Tiers

| Tier | Count | Description |
|---|---|---|
| Tier 1 | 45 | Read-only: briefing, positions, P&L, alerts, market intel, analytics |
| Tier 2 | 16 | Writes (requires `FORTRESS_MCP_ALLOW_WRITES=1`): alerts, journal, orders, sync |
| **quantdata-mcp** | **50** | **Standalone MCP — per-ticker IV rank, GEX, order flow, vol skew, dark pool, and more** |

## Examples

See the `examples/` folder for sample scripts.

## Related

- [fortress-v4-api](https://github.com/citychip/fortress-v4-api) — Backend
- [fortress-install](https://github.com/citychip/fortress-install) — WSL install guide
- [quantdata-mcp](https://github.com/zzulanas/quantdata-mcp) — QuantData MCP server
