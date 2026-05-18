# Fortress MCP Server

> Connects Claude Desktop to your Fortress Dashboard via the MCP stdio transport, giving Claude direct access to your live options portfolio, market intelligence, and trading workflow tools.

**46 tools in two tiers** — 37 read-only tools always available, 9 write tools enabled via environment variable.

---

## Prerequisites

- Python 3.10+ on your local machine
- `mcp` and `httpx` packages: `pip install mcp httpx`
- [Claude Desktop](https://claude.ai/download) installed
- A running [Fortress API](https://github.com/citychip/fortress-api) instance with your bearer token

---

## Installation

### 1. Clone or copy the server file

```bash
git clone https://github.com/citychip/fortress-mcp.git
# or simply copy fortress_mcp.py to a permanent location, e.g. ~/fortress_mcp/
```

### 2. Configure Claude Desktop

Open your Claude Desktop config file:

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

Add the following to the `mcpServers` section (merge with any existing content):

```json
{
  "mcpServers": {
    "fortress-dashboard": {
      "command": "python3",
      "args": ["/path/to/fortress_mcp/fortress_mcp.py"],
      "env": {
        "FORTRESS_API_URL": "http://<your-vps-ip>:3000",
        "FORTRESS_API_TOKEN": "<your-bearer-token>"
      }
    }
  }
}
```

Replace `/path/to/fortress_mcp/fortress_mcp.py` with the actual path on your machine. Your bearer token is found in the Fortress dashboard under **Settings → Security**.

### 3. Restart Claude Desktop

Fully quit and relaunch Claude Desktop. The `fortress-dashboard` server will appear in the MCP tools panel.

---

## Enabling Write Tools (Tier 2)

Write tools are disabled by default. To enable them, add `FORTRESS_MCP_ALLOW_WRITES` to the env block:

```json
"env": {
  "FORTRESS_API_URL": "http://<your-vps-ip>:3000",
  "FORTRESS_API_TOKEN": "<your-bearer-token>",
  "FORTRESS_MCP_ALLOW_WRITES": "1"
}
```

Enable write tools only when you intend to use them, and remove the flag when done.

---

## Tier 1 Tools — Read (31 tools, always available)

| Tool | What it does |
|---|---|
| `get_briefing()` | Full portfolio briefing — the recommended starting point for any session |
| `get_positions(aggregated)` | Current option book with Greeks and strategy labels |
| `get_candidates()` | IV crush candidate scanner results |
| `get_calendar(window_days)` | Earnings calendar for the trading universe |
| `get_universe()` | Trading universe (tier1 / tier2 / macro / excluded) |
| `get_journal(limit)` | Recent trade journal entries |
| `get_alerts()` | Active profit-take and stop-loss alerts |
| `get_dp_floors_and_gex(ticker)` | Dark pool floors and GEX call/put walls for a ticker |
| `get_chart_data(ticker, period)` | OHLCV candles with overlay levels (DP, GEX, SMA) |
| `evaluate_stop_loss(ticker, ...)` | Multi-signal stop-loss verdict (§6) |
| `evaluate_roll(ticker, ...)` | Roll evaluation with top-3 candidates (§5) |
| `evaluate_post_earnings(ticker, ...)` | Post-earnings decision matrix (§10) |
| `validate_jade_lizard(...)` | Jade lizard credit-vs-width check (§2.E) |
| `get_spy_hedge_coverage()` | SPY hedge coverage ratio check (§2.D) |
| `pretrade_check(ticker, strategy)` | Full pre-trade gate (§3.3 → §4 → §7) |
| `get_capability(refresh)` | Greeks backend health probe (web_api vs bs_yfinance) |
| `get_ibkr_status()` | IBKR Web API connection status |
| `get_settings()` | All runtime configuration |
| `get_quantdata_reports(report, date)` | QuantData report retrieval |
| `get_market_intelligence()` | Market regime and macro overlay |
| `get_pending_orders(status)` | Order approval queue |
| `options_greeks(spot, strike, dte, iv, right)` | Black-Scholes Greeks (live or fallback) |
| `preview_order(order_id)` | IBKR whatif margin preview |
| `qd_get_dark_pool_levels(ticker)` | QuantData dark pool levels |
| `qd_get_iv_rank(ticker)` | IV rank and IV percentile |
| `qd_get_max_pain(ticker)` | Options max pain level |
| `qd_get_net_drift(ticker)` | Cumulative options premium flow |
| `qd_get_oi_change(ticker)` | Open interest change by strike |
| `qd_get_order_flow(ticker)` | Unusual options order flow |
| `get_pnl()` | P&L summary (realized + unrealized) |
| `get_playbook()` | Active strategy playbook and persona configuration |
| `get_pnl()` | P&L summary — unrealised P&L per position and portfolio totals |
| `get_trade_report()` | Full structured trade report — candidates, actions, concentration warnings, stop-loss flags |
| `get_chart_data(ticker, period, interval)` | OHLCV + technicals (SMA/RSI/MACD/BB) + GEX strike levels for a ticker |
| `get_vol_analytics(ticker)` | IV skew curve, term structure, and ATM IV ladder from live options chain |
| `get_position_limits(ticker)` | Max profit, max loss, net premium, and breakeven prices for open positions |
| `get_forward_pnl(ticker, target_price, target_date, iv_multiplier)` | BS-model P&L simulation at a target price/date with optional IV crush |

## Tier 2 Tools — Write (9 tools, require `FORTRESS_MCP_ALLOW_WRITES=1`)

| Tool | What it does |
|---|---|
| `add_journal_entry(...)` | Log a trade journal entry |
| `add_alert(...)` | Create a new profit-take or stop-loss alert |
| `update_alert(id, ...)` | Modify an existing alert |
| `delete_alert(id)` | Remove an alert |
| `update_calendar(ticker, ...)` | Update an earnings calendar entry |
| `add_excluded_ticker(ticker)` | Add a ticker to the exclusion list |
| `add_universe_ticker(ticker, tier)` | Add a ticker to the trading universe |
| `update_settings_section(section, data)` | Update a settings section |
| `trigger_ibkr_sync()` | Trigger a full IBKR positions sync |

---

## Example Prompts

The following prompts work well as starting points for a Claude Desktop session with Fortress connected:

- *"Give me the full portfolio briefing."*
- *"Run a pre-trade check on AAPL for a short strangle."*
- *"Should I roll my TSLA position? It has 28 DTE and is 0.25 delta."*
- *"Evaluate the post-earnings situation for NVDA — gap down 6%, IV crush 40%."*
- *"What are the DP floors and GEX walls for SPY right now?"*
- *"Check my SPY hedge coverage."*
- *"Validate a jade lizard: put at 180, call spread 200/205, credits 1.50 and 0.80."*
- *"Is live Greeks coverage active? Which backend is being used?"*
- *"Show me the pending orders in the approval queue."*

---

## Security Notes

The bearer token grants full read access to your live portfolio data. Keep it private and do not commit it to version control. The Fortress API runs on `127.0.0.1:8080` internally; nginx on port 3000 is the public endpoint. The MCP server connects to port 3000 by default. Write tools are off by default — enable only when needed and remove the flag when done. The MCP server never executes trades directly; it only reads data and writes to the dashboard's internal state.

---

## Related Repositories

| Repository | Description |
|---|---|
| [citychip/fortress-api](https://github.com/citychip/fortress-api) | FastAPI backend — the data source for all MCP tools |
| [citychip/fortress-app](https://github.com/citychip/fortress-app) | React 19 + tRPC frontend — the dashboard UI |
