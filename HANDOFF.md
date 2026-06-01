# Fortress Dashboard — Session Handoff
**Date:** 2026-05-30 | **For:** Next Cowork session
**⚠️ DELETE THIS FILE after next session starts — contains git token**

---

## System Overview

Fortress is a personal options trading dashboard running **entirely on WSL (Ubuntu) on Windows**. No VPS — the old Hostinger VPS (`srv1321374.hstgr.cloud`) still runs v1.2.0 but is outdated and should be ignored.

**Stack:**
- Backend: FastAPI at `http://localhost:8081` — `~/fortress-v4-api/` (WSL)
- Frontend: React/Vite, served by nginx at `http://localhost` — `~/fortress-v4-frontend/` (WSL)
- MCP server: `C:\Users\cityc.000\fortress_mcp\fortress_mcp.py` (Windows)
- IBKR: CP Gateway at `https://localhost:5000` (requires daily browser login)
- QuantData: JWT stored at `~/.quantdata-mcp/config.json`

**Service management:**
```bash
sudo systemctl restart fortress-dashboard-v4
sudo systemctl status fortress-dashboard-v4
journalctl -u fortress-dashboard-v4 -n 50 --no-pager
```

**Frontend deploy after changes:**
```bash
cd ~/fortress-v4-frontend && npm run build
sudo cp -r dist/public/* /var/www/fortress-v4/
sudo nginx -s reload
```

**API token:** `07f03fb6e664859ac5e8113eaf1102ac43a3cb785c581af756671072b426db21`

---

## GitHub Repos

| Repo | Branch | Purpose |
|---|---|---|
| `citychip/fortress-v4-api` | `main` | Backend, quant scripts, docs |
| `citychip/fortress-mcp` | `master` | MCP server for Claude |
| `citychip/fortress-v4-frontend` | `main` | React frontend |
| `citychip/quantdata-mcp` | — | Keep for reference only |

**Git auth token:** `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`

Set on WSL:
```bash
git -C ~/fortress-v4-api remote set-url origin https://citychip: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@github.com/citychip/fortress-v4-api.git
git -C ~/fortress-v4-frontend remote set-url origin https://citychip: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@github.com/citychip/fortress-v4-frontend.git
```

---

## Key File Paths

| What | Path |
|---|---|
| Backend routes | `~/fortress-v4-api/app/routes/` |
| Quant scripts + state JSON | `~/fortress-v4-api/quant/` |
| Frontend pages | `~/fortress-v4-frontend/client/src/pages/` |
| Theme constants (SINGLE SOURCE) | `~/fortress-v4-frontend/client/src/lib/theme.ts` |
| MCP server | `C:\Users\cityc.000\fortress_mcp\fortress_mcp.py` |
| QuantData config | `~/.quantdata-mcp/config.json` + `/root/.quantdata-mcp/config.json` |
| Systemd service | `/etc/systemd/system/fortress-dashboard-v4.service` |
| Nginx config | `/etc/nginx/sites-available/fortress-v4` → `/var/www/fortress-v4/` |
| Master doc | `~/fortress-v4-api/docs/FORTRESS_V4_MASTER_DOC.md` |
| Sprint plan | `~/fortress-v4-api/docs/SPRINT_PLAN_v4.2.md` |
| Quick start cheatsheet | `~/fortress-v4-api/docs/operations/03_Quick_Start_and_Daily_Cheatsheet.md` |
| Todo backlog | `~/fortress-v4-api/docs/review/11_Todo_Backlog.md` |

---

## Morning Startup Sequence

1. `sudo systemctl status fortress-dashboard-v4` — confirm running
2. MCP: `get_briefing()` — Net Liq, regime, concentration, pacing
3. MCP: `get_market_intelligence("SPY")` — macro regime for the day
4. MCP: `get_candidates()` — IVR scan (auto-refreshed at 07:00 ET weekdays)
5. For IVR > 50 with earnings > 21 days: `pretrade_check(ticker)`
6. Execute after 10:00 AM ET only

---

## Current Portfolio State (2026-05-30)

- Net Liq: ~$91,142 | Excess Liq: $33,366 | Available: $27,587
- Regime: **Bearish** | VIX: 15.32
- MSFT concentration: **97.1%** (acceptable per §3.1 MSFT exception — but no new entries)
- Pacing: 0/5 trades used this week
- Active: MSFT (PMCC), AMZN (PMCC), GOOGL (PMCC), NVDA (PMCC), AMD (PCS), OST (Stock)

**Top IV crush candidates (Monday open):**
- TSM: IVR 87.6, +10.3pp 🔥 PRIME (earnings 46d out)
- AVGO: IVR 100 — **BLOCKED** (earnings ~Tuesday)
- V: IVR 56.4, +7.5pp ✅
- NVDA: IVR 83, +7.4pp ✅
- MSFT: blocked (concentration)

---

## What Was Done This Session (2026-05-30)

- **v8.10** IBKR upload retry — `retry_ibkr_sync()` MCP tool
- **v8.11** Ticker universe path fix — scripts scan 18 tickers (not 11)
- **v8.12** Regime label formatting — Title Case in API
- **v8.13** Market Intel server-side 5-min cache + Refresh All button
- **v8.14** Market Intel portfolio/universe split with position badges
- **v8.15** QuantData auto-refresh — daily 06:00 ET APScheduler
- **v8.16** Premarket + IV crush schedules confirmed running
- Security: /api/token localhost-only, CORS restricted, sensitive files gitignored
- Code: colour constants → `lib/theme.ts` (16 files), `requests` removed from MCP
- Docs: MASTER_DOC v4.3, SPRINT_PLAN, Quick Start Cheatsheet, Todo Backlog all updated
- All uncommitted changes committed and pushed

---

## Known Limitation — QuantData Per-Ticker (v8.9 — Won't Fix)

All `qd_*` MCP tools return **SPY data only** regardless of ticker passed. Root cause: `PUT /api/tool` (update_tool) returns HTTP 200 but QuantData ignores the filter change. Proven by direct testing 2026-05-30.

**Use instead:**
- For IVR: `get_candidates()` or `run_script("iv_crush")` — yfinance, accurate per-ticker
- For dark pool / order flow: use the dashboard UI directly

**Future fix path (Option A):** Create per-ticker tool instances via `POST /api/tool` (~108 UUIDs for 18 tickers × 6 tools). See `docs/FORTRESS_V4_MASTER_DOC.md §6`.

---

## What Remains (backlog)

Quick wins (< 1h):
- `qd_status()` MCP tool — check if QD working before calling qd_*
- Regime badge colour (red → amber/green)
- DTE countdown on Earnings rows
- Fix `dashboardName: "Fortress v3"` in user_prefs.json

Medium (1–3h):
- Colour-coded Quick Nav cards on Dashboard
- Collapse IBKR Sync panel when current
- Collapsible position groups on Portfolio page
- Standardise backend logging (print → logger.*)

Larger:
- Split SettingsPage.tsx (1,692 lines) into sub-components
- Split AnalysisPage.tsx (1,469 lines) into sub-components
- Frontend unit tests (msw-based)
- MySQL migration for alerts/journal

---

## Important Notes

- **After backend change:** `sudo systemctl restart fortress-dashboard-v4`
- **After frontend change:** build + copy + nginx reload
- **After MCP change:** fully quit and relaunch Claude Desktop
- **Colour constants:** always import from `@/lib/theme` — never redeclare locally
- **QuantData session** auto-refreshes at 06:00 ET. Manual: Settings → QuantData Auto-Login, then `sudo cp ~/.quantdata-mcp/config.json /root/.quantdata-mcp/config.json`
- **IBKR** requires daily browser login at `https://localhost:5000`
- **ibind OAuth 1.0a** configured but pending IBKR activation — toggle in Settings → Security when ready
- **Workflow scripts** output `.md` reports to `~/fortress-v4-api/quant/` (gitignored)

---

## Strategy Quick Reference (v3.7.2)

- IVR > 25 required before any new put spread; > 50 = prime
- No new entries within 10 days of earnings (PCS) or 14 days (LEAP)
- Execute after 10:00 AM ET
- Max 2 new positions per week
- MSFT: concentration exception (currently 97% — no new entries until reduced)
- SPY hedge required when Net Liq > $50K
- Delta target: 0.35 net long | Critical roll threshold: delta > 0.35 on short call
