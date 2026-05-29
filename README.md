# Fortress MCP Server

MCP server connecting Claude to the Fortress Trading Dashboard V4.
64 tools across portfolio analysis, IBKR management, options strategy, and QuantData market data.

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

3. Add the config snippet to Claude Desktop's `claude_desktop_config.json`:
   - Windows path: `%APPDATA%\Claude\claude_desktop_config.json`
   - Merge the contents of `claude_desktop_config_snippet.json` into it

4. Restart Claude Desktop

## Configuration

The `claude_desktop_config_snippet.json` is pre-configured for local WSL use:
- `FORTRESS_API_URL`: `http://localhost:8081`
- `FORTRESS_API_TOKEN`: your bearer token

**QuantData credentials are not required on the client.** All `qd_*` tools proxy through the Fortress server, which holds the QD JWT server-side. No `QUANTDATA_AUTH_TOKEN` or `QUANTDATA_INSTANCE_ID` env vars needed.

## Tool Tiers

| Tier | Count | Description |
|---|---|---|
| Tier 1 | 45 | Read-only: briefing, positions, P&L, alerts, market intel, analytics |
| Tier 2 | 10 | Writes (requires `FORTRESS_MCP_ALLOW_WRITES=1`): alerts, journal, sync |
| QD | 6 | QuantData live data: IV rank, dark pool, order flow, max pain |
| Charts | 3 | Chart data, GEX, order flow overlays |

## Examples

See the `examples/` folder for sample scripts.

## Related

- [fortress-v4-api](https://github.com/citychip/fortress-v4-api) — Backend
- [fortress-install](https://github.com/citychip/fortress-install) — WSL install guide
