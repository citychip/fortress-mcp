# Fortress V3 — Design Specification

## Priority 1: Smart Refresh (Differential Polling) — ~1 day

**What changes:** Replace the single global poll interval with per-layer refresh rates.

**Files to touch:**
- `useApi.ts` — extend `useApiData()` to accept optional `intervalMs` param (default 30s for backward compat)
- `App.tsx` — pass correct rates per page/component

**Refresh tier map:**
| Interval | Data |
|---|---|
| 250ms | Top bar: Net Liq, SPY price (summary fields only, not full briefing) |
| 1s | Greeks cockpit (delta, theta, vega on open positions) |
| 10s | IBKR sync status |
| 30s | Positions list |
| 5 min | Candidates scanner, earnings calendar |

---

## Priority 1: Volatility Surface Panel — ~3 days

**Where it lives:** New tab in the Greeks Cockpit. Tab pills: `Greeks | Vol Surface | Term Structure`

**New backend endpoint:** `GET /api/options/vol-surface?ticker=SPY`
- Returns strike × expiry grid of IVs
- Use existing option chain data + QuantData IV data
- Fill gaps with `scipy.interpolate.RegularGridInterpolator`
- Response: `{ strikes: [], expiries: [], iv_grid: [[]] }`

**Frontend:** `react-plotly.js` with `surface` trace type
- X axis: Strike price
- Y axis: Days to expiry (DTE)
- Z axis: Implied Volatility %
- Overlay: current position strikes as scatter dots (red = short, blue = long)
- Controls: drag to rotate, ticker input, toggle "highlight my strikes"

**Summary bar below surface:**
- ATM IV, Skew (25Δ), IVR, Term slope

---

## Priority 2: Push Notifications on Alert Triggers — ~1 day

**Trigger events:**
- Stop-loss threshold breach
- Profit-take target hit
- Earnings within 48h for a held position
- IV rank crosses 30 or 70
- Order approved / rejected in IBKR

**Recommended delivery: Telegram bot** (free, instant, rich formatting)
- Config: `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` env vars in `/etc/systemd/system/fortress-dashboard.service`

**Architecture:**
- New file: `/home/ubuntu/Fortress_Dashboard/app/services/notifier.py`
- Async function: `send_alert(event: str, ticker: str, message: str)`
- Call from existing alert evaluation endpoints (`evaluate_stop_loss`, `evaluate_roll`, etc.)

**Telegram message format:**
```
🔴 STOP-LOSS — MSFT
Put 390 exp 30 May
Stock: $382.40 (−2.1%)
Position P&L: −$340 (−68%)
Signal: Price below §6 floor
Fortress · 14:23 ET
```

---

## Priority 3: Mobile Alert View — ~2 days

**Scope:** Single responsive route `/mobile` — read-only triage view.
- Not a full mobile port. Desktop features stay desktop-only.
- Viewport: 390px optimised

**What's included:**
- Net Liq + Day P&L (large, top of screen)
- Active alerts list (stop-loss / profit-take signals)
- Positions summary (count, how many expiring < 7 days)
- Pending orders badge

**What's excluded:** Build Center, Approvals, Greeks, Charts, Journal

---

## Current stack reference
- Backend: FastAPI on `127.0.0.1:8080`, served via nginx on port 3000
- Frontend: React + TypeScript + Tailwind 4 + wouter, built to `/var/www/fortress-v2/`
- MCP: 40 tools (`citychip/fortress-mcp`), calls `http://76.13.138.194:3000`
- Repos: `citychip/fortress-api` (master), `citychip/fortress-app` (main), `citychip/fortress-mcp` (main)
