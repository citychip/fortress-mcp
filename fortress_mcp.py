#!/usr/bin/env python3
"""
fortress_mcp.py — Fortress Dashboard MCP Server
Tier 1 (read-only tools) + Tier 2 (write tools, env-gated)

Transport: stdio (launched by Claude Desktop as a subprocess)
Auth:      Bearer token via FORTRESS_API_TOKEN env var
Writes:    Enabled only when FORTRESS_MCP_ALLOW_WRITES=1

QuantData: handled by the standalone quantdata-mcp server (registered
  separately in claude_desktop_config.json). The 6 legacy qd_* proxy
  tools have been removed — use the quantdata MCP directly for all
  per-ticker IV rank, order flow, dark pool, GEX, and vol data.

Usage:
    export FORTRESS_API_URL=http://localhost:8081
    export FORTRESS_API_TOKEN=your-64-char-token
    python3 fortress_mcp.py
"""

import os
import json
import time
import logging
from typing import Optional, Any
import httpx
from mcp.server.fastmcp import FastMCP
FORTRESS_MCP_VERSION = "4.9.0"


logger = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────
API_URL   = os.environ.get("FORTRESS_API_URL", "http://localhost:8081").rstrip("/")
API_TOKEN = os.environ.get("FORTRESS_API_TOKEN", "")
ALLOW_WRITES = os.environ.get("FORTRESS_MCP_ALLOW_WRITES", "0") == "1"

mcp = FastMCP(
    "fortress-dashboard",
    instructions=(
        "Fortress Dashboard MCP v4.5.1 — Portfolio Strategy v3.9.0. "
        "All monetary values are USD. Delta target: 0.35 net long. "
        "Use get_briefing() first for any portfolio question. "
        "Never execute trades — this server is read-only unless FORTRESS_MCP_ALLOW_WRITES=1. "
        "IV RANK: use THIS server's get_iv_rank() (backend yfinance, BS-inverted from "
        "lastPrice) — do NOT use quantdata's iv_rank, it is broken upstream (ticker "
        "argument ignored; every ticker returns identical values, verified 2026-06-10). "
        "quantdata's volatility_skew and exposure_by_strike are also broken during market "
        "hours. Use the quantdata MCP only for: order flow, dark pool levels, max pain, "
        "OI, net flow. For GEX and vol skew use this server's get_gex()/get_vol_skew(). "
        "Since 2026-06-10 the backend is IBKR-first: spot (incl. conditional-alert "
        "evaluation), liquidity bid/ask, IV rank, and vol skew pull real-time data from "
        "IBKR CP Gateway. Payloads carry source/iv_source: 'ibkr' = live gateway data; "
        "'bs_inversion'/'yfinance_bs' = BS-inverted yfinance fallback (~15m delayed, "
        "sane). The old Yahoo-IV-column / delayed-feed caveat no longer applies."
    ),
)

# ─── HTTP client ─────────────────────────────────────────────────────────────
def _client() -> httpx.Client:
    return httpx.Client(
        base_url=API_URL,
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        timeout=30,
        verify=False,  # self-signed cert on VPS
    )

def _get(path: str, params: dict | None = None) -> Any:
    with _client() as c:
        r = c.get(path, params=params)
        r.raise_for_status()
        return r.json()

def _post(path: str, body: dict | None = None, params: dict | None = None) -> Any:
    with _client() as c:
        r = c.post(path, json=body or {}, params=params)
        r.raise_for_status()
        return r.json()

def _put(path: str, body: dict) -> Any:
    with _client() as c:
        r = c.put(path, json=body)
        r.raise_for_status()
        return r.json()

def _patch(path: str, body: dict) -> Any:
    with _client() as c:
        r = c.patch(path, json=body)
        r.raise_for_status()
        return r.json()

def _delete(path: str) -> Any:
    with _client() as c:
        r = c.delete(path)
        r.raise_for_status()
        return r.json()

def _writes_check() -> None:
    if not ALLOW_WRITES:
        raise PermissionError(
            "Write tools are disabled. Set FORTRESS_MCP_ALLOW_WRITES=1 to enable."
        )

# ─── Tier 1 — Read-only tools ─────────────────────────────────────────────────

@mcp.tool()
def get_briefing() -> dict:
    """
    Full portfolio briefing: account header (NetLiq, delta, pacing), today's
    required actions, market regime, concentration top-5, Portfolio Greeks
    (delta/theta/vega), FX rates, USD threshold check, and data staleness.
    Call this first for any portfolio question.
    """
    return _get("/api/briefing")

@mcp.tool()
def get_positions(aggregated: bool = True) -> dict:
    """
    Current option book. aggregated=True (default) returns one row per ticker
    with combined delta/theta/vega. aggregated=False returns one row per leg.
    Includes stop-loss status, DTE, and Greeks per position.
    """
    if aggregated:
        return _get("/api/manage/positions")
    return _get("/api/positions")

@mcp.tool()
def get_candidates() -> dict:
    """
    IV crush candidate scanner: tickers ranked by IVR and IV/HV spread,
    enriched with earnings blackout status, concentration check, exclusion
    flags, and a tradeable signal. Use before any new trade decision.
    """
    return _get("/api/candidates")

@mcp.tool()
def get_calendar(window_days: int = 14) -> dict:
    """
    Earnings calendar for the next window_days (default 14). Returns each
    ticker's next earnings date, days-to-earnings, and confirmation status.
    Critical for pre-trade gate §3.3 (no new positions within 7 days of earnings).
    """
    return _get("/api/calendar", params={"window_days": window_days})

@mcp.tool()
def get_universe() -> dict:
    """
    Full trading universe: tier1 (core watchlist), tier2 (secondary),
    macro (SPX/SPY/VIX), and excluded tickers with exclusion reasons.
    """
    return _get("/api/universe")

@mcp.tool()
def get_journal(limit: int = 30) -> dict:
    """
    Recent trade journal entries (default last 30). Each entry includes
    action type, ticker, reasoning, framework rules cited, and outcome
    metrics where available. Use for decision audit trail.
    """
    return _get("/api/journal", params={"limit": limit})

@mcp.tool()
def get_alerts() -> dict:
    """
    Active profit-take and stop-loss alerts. Each alert includes position ID,
    trigger type (delta/price/pnl), trigger value, direction, and action.
    """
    return _get("/api/alerts")

@mcp.tool()
def get_dp_floors_and_gex(ticker: str) -> dict:
    """
    DP floors and GEX walls for a ticker from the latest QuantData Daily Report.
    Returns key support/resistance levels used in stop-loss and roll decisions.
    ticker: uppercase ticker symbol, e.g. 'AAPL', 'SPY'
    """
    return _get(f"/api/chart/{ticker}/levels")

@mcp.tool()
def get_market_intelligence(ticker: str = "SPY", refresh: bool = False) -> dict:
    """
    Full market intelligence synthesis for a ticker: regime score (-4 to +4),
    GEX gamma flip zone, dark pool floors, net drift, and specific trade setups.
    This is the most sophisticated output the Fortress system produces — use it
    every morning before placing trades and when evaluating directional bias.
    ticker: uppercase ticker symbol, e.g. 'SPY', 'QQQ', 'AAPL'. Defaults to 'SPY'.
    refresh: set True to bypass the 5-minute server cache and fetch live data.
             Default False returns cached data instantly. Use refresh=True when
             you need the latest data after market-moving events.
    """
    return _get("/api/market-intelligence", params={"ticker": ticker, "refresh": refresh})

@mcp.tool()
def evaluate_stop_loss(
    ticker: str,
    fundamental_break: bool = False,
    peak_mv: Optional[float] = None,
) -> dict:
    """
    Multi-signal stop-loss verdict for a position per Strategy §6.
    Returns: hold / close / reduce recommendation with signal breakdown.
    ticker: uppercase ticker symbol
    fundamental_break: True if a thesis-invalidating event has occurred
    peak_mv: peak market value of the position if known (for drawdown calc)
    """
    params: dict = {"fundamental_break": str(fundamental_break).lower()}
    if peak_mv is not None:
        params["peak_mv"] = peak_mv
    return _get(f"/api/manage/stop_loss/{ticker}", params=params)

@mcp.tool()
def evaluate_roll(
    ticker: str,
    dte_low: int = 30,
    dte_high: int = 45,
    delta_low: float = 0.20,
    delta_high: float = 0.25,
) -> dict:
    """
    Roll evaluation for an expiring position per Strategy §5.
    Returns top-3 roll candidates with strike/expiry/credit and IBKR ticket text.
    ticker: uppercase ticker symbol
    dte_low/dte_high: target DTE window for the rolled position
    delta_low/delta_high: target delta range for the rolled strike
    """
    return _get(
        f"/api/manage/roll/{ticker}",
        params={
            "dte_low": dte_low,
            "dte_high": dte_high,
            "delta_low": delta_low,
            "delta_high": delta_high,
        },
    )

@mcp.tool()
def evaluate_post_earnings(
    ticker: str,
    gap_pct: float,
    iv_crush_pct: float,
    thesis: Optional[dict] = None,
) -> dict:
    """
    Post-earnings decision matrix per Strategy §10.
    Returns: hold / close / adjust verdict with reasoning.
    ticker: uppercase ticker symbol
    gap_pct: overnight gap as a percentage (negative = gap down), e.g. -4.5
    iv_crush_pct: IV crush magnitude as a percentage, e.g. 35.0
    thesis: optional dict with original trade thesis fields
    """
    body: dict = {"ticker": ticker, "gap_pct": gap_pct, "iv_crush_pct": iv_crush_pct}
    if thesis:
        body["thesis"] = thesis
    return _post("/api/playbook/post_earnings", body=body)

@mcp.tool()
def validate_jade_lizard(
    put_strike: float,
    call_short_strike: float,
    call_long_strike: float,
    put_credit: float,
    call_spread_credit: float,
) -> dict:
    """
    Validate a jade lizard structure per Strategy §2.E.
    Checks that total credit > width of call spread (no upside risk).
    Returns: valid/invalid with credit breakdown and risk assessment.
    All strikes and credits in USD.
    """
    return _post(
        "/api/manage/validate_jade_lizard",
        body={
            "put_strike": put_strike,
            "call_short_strike": call_short_strike,
            "call_long_strike": call_long_strike,
            "put_credit": put_credit,
            "call_spread_credit": call_spread_credit,
        },
    )

@mcp.tool()
def get_spy_hedge_coverage() -> dict:
    """
    SPY hedge coverage check per Strategy §2.D (USD-native in v3.6).
    Returns: current hedge notional, required coverage, gap, and verdict.
    """
    return _get("/api/manage/spy_hedge_coverage")

@mcp.tool()
def pretrade_check(ticker: str, strategy: str) -> dict:
    """
    Full pre-trade gate check per Strategy §3.3 → §4 → §7.
    Runs: exclusion check, earnings blackout (7-day window), concentration
    limit (Strategy §3.4), and VIX regime gate.
    ticker: uppercase ticker symbol, e.g. 'AAPL'
    strategy: strategy type, e.g. 'short_put', 'short_strangle', 'jade_lizard'
    Returns: go / no-go with per-gate breakdown.
    """
    return _get("/api/manage/pre_trade_check", params={"ticker": ticker, "strategy": strategy})

@mcp.tool()
def get_capability(refresh: bool = False) -> dict:
    """
    Greeks backend capability probe: Web API (CP Gateway + OPRA) and legacy
    TWS gateway status. Use to answer 'Is live Greeks coverage active right now?'
    refresh=True forces a fresh probe (otherwise returns cached result, ~60s TTL).
    Returns: active_backend, session status, OPRA subscription, checked_at.
    """
    return _get("/api/ibkr/capability", params={"refresh": str(refresh).lower()})

@mcp.tool()
def get_ibkr_status() -> dict:
    """
    IBKR / Greeks backend status — returns active backend, session health,
    OPRA subscription status, and last checked timestamp.
    Wraps /api/ibkr/capability (the /api/ibkr/status legacy route has a
    known bug and is bypassed here).
    For a detailed capability probe with refresh, call get_capability().
    """
    return _get("/api/ibkr/capability")

@mcp.tool()
def get_settings() -> dict:
    """
    All current runtime configuration: strategy thresholds, alert thresholds,
    technical/infrastructure settings (Greeks backend, gateway URLs, API keys
    masked), and UI preferences.
    Returns: {config: {strategy: {...}, alerts: {...}, technical: {...}, ui: {...}}}
    """
    return _get("/api/settings")

@mcp.tool()
def get_quantdata_reports(report: str = "daily", date: str = "latest") -> dict:
    """
    Retrieve a QuantData report from the VPS filesystem.
    report: report type — 'daily', 'weekly', or 'options'
    date: 'latest' (default) or a date string 'YYYY-MM-DD'
    Returns the full report text and metadata.
    """
    return _get("/api/uploads", params={"report": report, "date": date})

# ─── Tier 2 — Write tools (env-gated) ────────────────────────────────────────

@mcp.tool()
def add_journal_entry(
    action: str,
    ticker: str,
    description: str,
    reasoning: str,
    framework_rules: list[str],
    outcome: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Append a new entry to the trade journal.
    action: e.g. 'open', 'close', 'roll', 'adjust', 'observe'
    ticker: uppercase ticker symbol
    description: one-sentence summary of the action taken
    reasoning: detailed reasoning referencing strategy framework
    framework_rules: list of strategy section references, e.g. ['§3.3', '§6.2']
    outcome: optional outcome description (for post-trade entries)
    tags: optional list of tags, e.g. ['earnings', 'roll', 'stop-loss']
    """
    _writes_check()
    body: dict = {
        "action": action,
        "ticker": ticker,
        "description": description,
        "reasoning": reasoning,
        "framework_rules": framework_rules,
    }
    if outcome:
        body["outcome"] = outcome
    if tags:
        body["tags"] = tags
    return _post("/api/journal", body=body)

@mcp.tool()
def add_alert(
    ticker: str,
    message: str,
    severity: str = "info",
    position_id: Optional[str] = None,
) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Add a NOTIFICATION alert (message feed — does NOT auto-trigger).
    For price/delta/DTE/P&L triggers use add_conditional_alert() instead.
    Matches backend POST /api/alerts AlertCreate schema (verified via
    openapi.json 2026-06-10).
    ticker: uppercase ticker, e.g. 'MSFT' (max 10 chars)
    message: alert text, 1-500 chars (REQUIRED)
    severity: 'info' | 'warn' | 'critical' (default 'info')
    position_id: optional linked position synthetic ID
    """
    _writes_check()
    body: dict = {"ticker": ticker, "message": message, "severity": severity, "source": "claude"}
    if position_id is not None:
        body["position_id"] = position_id
    return _post("/api/alerts", body=body)

@mcp.tool()
def update_alert(
    alert_id: str,
    severity: Optional[str] = None,
    message: Optional[str] = None,
    snoozed: Optional[bool] = None,
) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Update a notification alert. Matches backend PATCH /api/alerts/{id}
    AlertUpdate schema: severity ('info'|'warn'|'critical'), message,
    snoozed. (Fixed 2026-06-10: previous body {trigger_value, action,
    active} fields were silently ignored by the backend.)
    alert_id: alert identifier from get_alerts()
    """
    _writes_check()
    body: dict = {}
    if severity is not None:
        body["severity"] = severity
    if message is not None:
        body["message"] = message
    if snoozed is not None:
        body["snoozed"] = snoozed
    return _patch(f"/api/alerts/{alert_id}", body=body)

@mcp.tool()
def get_conditional_alerts(ticker: Optional[str] = None) -> dict:
    """
    List conditional (auto-evaluated trigger) alerts, optionally filtered
    by ticker. These are evaluated by the scheduler's alert_eval job
    (every few minutes during RTH). Each alert: id, ticker, alert_type,
    threshold, message, urgency, triggered, snoozed.
    """
    path = "/api/conditional-alerts"
    if ticker:
        path += f"?ticker={ticker}"
    return _get(path)

@mcp.tool()
def add_conditional_alert(
    ticker: str,
    alert_type: str,
    threshold: float,
    message: str,
    urgency: str = "watch",
    position_id: Optional[str] = None,
    action_mode: Optional[str] = "new",
) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Add a CONDITIONAL alert — auto-evaluated against live data by the
    scheduler (alert_eval job). Use this for price/delta/DTE/P&L triggers.
    ticker: uppercase ticker, e.g. 'MSFT'
    alert_type: 'price_above' | 'price_below' | 'pnl_pct' | 'dte_lte'
                | 'delta_gte' | 'conditional_entry'
    threshold: trigger value (price, %, DTE, or delta)
    message: alert text, 1-300 chars
    urgency: 'critical' | 'watch' | 'profit' | 'entry' (default 'watch')
    position_id: optional linked position synthetic ID
    action_mode: 'new' | 'roll' | 'close' | 'add' (default 'new')
    """
    _writes_check()
    body: dict = {
        "ticker": ticker,
        "alert_type": alert_type,
        "threshold": threshold,
        "message": message,
        "urgency": urgency,
        "action_mode": action_mode or "new",
    }
    if position_id is not None:
        body["position_id"] = position_id
    return _post("/api/conditional-alerts", body=body)

@mcp.tool()
def update_conditional_alert(
    alert_id: str,
    threshold: Optional[float] = None,
    message: Optional[str] = None,
    snoozed: Optional[bool] = None,
) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Update a conditional alert. Changing threshold re-arms the alert
    (triggered reset to False). snoozed=True pauses evaluation.
    alert_id: id from get_conditional_alerts()
    """
    _writes_check()
    body: dict = {}
    if threshold is not None:
        body["threshold"] = threshold
    if message is not None:
        body["message"] = message
    if snoozed is not None:
        body["snoozed"] = snoozed
    return _patch(f"/api/conditional-alerts/{alert_id}", body=body)

@mcp.tool()
def delete_conditional_alert(alert_id: str) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Delete a conditional alert by ID.
    alert_id: id from get_conditional_alerts()
    """
    _writes_check()
    return _delete(f"/api/conditional-alerts/{alert_id}")

@mcp.tool()
def evaluate_conditional_alerts() -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Force an immediate evaluation pass of all active conditional alerts
    (normally run by the scheduler). Returns newly triggered alerts.
    """
    _writes_check()
    return _post("/api/conditional-alerts/evaluate", body={})

@mcp.tool()
def delete_alert(alert_id: str) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Delete an alert by ID. Reversible from backups.
    alert_id: alert identifier from get_alerts()
    """
    _writes_check()
    return _delete(f"/api/alerts/{alert_id}")

@mcp.tool()
def update_calendar(
    ticker: str,
    next_earnings: str,
    confirmed: bool = False,
) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Update the earnings date for a ticker.
    ticker: uppercase ticker symbol
    next_earnings: date string 'YYYY-MM-DD'
    confirmed: True if date is confirmed (not estimated)
    Affects pre-trade earnings blackout gate (§3.3).
    """
    _writes_check()
    return _put(f"/api/calendar/{ticker}", body={
        "next_earnings": next_earnings,
        "confirmed": confirmed,
    })

@mcp.tool()
def add_excluded_ticker(ticker: str, reason: str) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Add a ticker to the exclusion list.
    ticker: uppercase ticker symbol
    reason: human-readable reason for exclusion
    """
    _writes_check()
    return _post("/api/universe/exclude", body={"ticker": ticker, "reason": reason})

@mcp.tool()
def add_universe_ticker(tier: str, ticker: str) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Add a ticker to the trading universe.
    tier: 'tier1', 'tier2', or 'macro'
    ticker: uppercase ticker symbol
    Note: tier composition changes require manual review per Strategy §3.4.4.
    """
    _writes_check()
    return _post("/api/universe/add", body={"tier": tier, "ticker": ticker})

@mcp.tool()
def update_settings_section(section: str, values: dict) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Update a settings section. Only use when explicitly approved by user in chat.
    section: 'strategy', 'alerts', 'technical', or 'ui'
    values: dict of key-value pairs to update, e.g. {"delta_target": 0.35}
    Use get_settings() first to see current values and valid keys.
    """
    _writes_check()
    return _put(f"/api/settings/{section}", body={"values": values})

@mcp.tool()
def trigger_ibkr_sync(backend: Optional[str] = None) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Trigger an IBKR positions and Greeks sync.
    backend: override backend — 'web_api', 'bs_yfinance', 'tws_ibkr', or None for auto.
    Atomic operation with backup. Use sparingly — sync runs automatically every 60s.
    """
    _writes_check()
    body: dict = {}
    if backend:
        body["backend"] = backend
    return _post("/api/ibkr/sync", body=body)

@mcp.tool()
def retry_ibkr_sync() -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Retry the last failed IBKR sync (K-03 fix).
    Re-runs the same sync pipeline using the same backend as the previous attempt.
    Use when a sync failed due to a transient error (network drop, gateway timeout).
    Falls back to a fresh sync if no prior attempt is recorded.
    """
    _writes_check()
    return _post("/api/ibkr/upload/retry")

# ─── Orders ───────────────────────────────────────────────────────────────────

@mcp.tool()
def get_pending_orders(status=None):
    """
    List orders in the approval queue submitted from Build Center.
    status filter: pending | submitted | declined | failed | None for all.
    Each order shows ticker, strategy, legs, PoP, max profit/loss, whatif result.
    """
    params = {"status": status} if status else None
    return _get("/api/orders/pending", params=params)

@mcp.tool()
def stage_order(
    ticker: str,
    strategy: str,
    legs: list,
    quantity: int = 1,
    order_type: str = "LMT",
    limit_price: float = None,
    notes: str = None,
    pop: float = None,
    max_profit: float = None,
    max_loss: float = None,
) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Stage a new order in the Fortress Build Center approval queue.

    Args:
        ticker:      Primary underlying, e.g. "MSFT"
        strategy:    Strategy label, e.g. "PMCC", "CSP", "IC", "PCS"
        legs:        List of leg dicts. Each leg needs:
                       ticker, sec_type ("OPT"|"STK"), right ("C"|"P"),
                       strike (float), expiry ("YYYYMMDD"),
                       action ("BUY"|"SELL"), ratio (int, default 1)
                     Example:
                       [{"ticker":"MSFT","sec_type":"OPT","right":"C",
                         "strike":490.0,"expiry":"20260821",
                         "action":"SELL","ratio":1}]
        quantity:    Number of contracts (default 1)
        order_type:  "LMT" (default), "MKT", or "MOC"
        limit_price: Limit price per contract (required for LMT)
        notes:       Optional trade rationale
        pop:         Probability of profit estimate (0.0–1.0)
        max_profit:  Max profit in USD
        max_loss:    Max loss in USD (negative for debit)

    Returns dict with order_id. Next: preview_order(id) → approve_order(id).
    """
    _writes_check()
    payload = {
        "ticker":       ticker.upper(),
        "strategy":     strategy,
        "legs":         legs,
        "quantity":     quantity,
        "order_type":   order_type,
        "action":       "SELL",
        "limit_price":  limit_price,
        "notes":        notes,
        "submitted_by": "MCP",
        "pop":          pop,
        "max_profit":   max_profit,
        "max_loss":     max_loss,
    }
    data = _post("/api/orders/pending", body=payload)
    order_id = data.get("id", "unknown")
    return {
        "ok":       True,
        "order_id": order_id,
        "status":   data.get("status", "pending"),
        "message":  (
            f"Order staged (id={order_id}). "
            f"Run preview_order('{order_id}') to check margin, "
            f"then approve_order('{order_id}') to submit to IBKR."
        ),
        "order": data,
    }

@mcp.tool()
def preview_order(order_id: str):
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    IBKR whatif (margin/commission estimate) for a pending order — no submission.
    Returns equity impact, init margin, maintenance margin, commission estimate.
    """
    _writes_check()
    return _post(f"/api/orders/pending/{order_id}/preview")

@mcp.tool()
def approve_order(order_id: str):
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Approve a pending order: resolves IBKR conids, runs whatif, submits to IBKR.
    Returns submitted status and IBKR order ID on success.
    """
    _writes_check()
    return _post(f"/api/orders/pending/{order_id}/approve")

@mcp.tool()
def decline_order(order_id: str):
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Decline a pending order. Sets status to declined.
    """
    _writes_check()
    return _delete(f"/api/orders/pending/{order_id}")

# ─── Options & Greeks ─────────────────────────────────────────────────────────

@mcp.tool()
def options_greeks(spot: float, strike: float, dte: int, iv: float, right: str, qty=None):
    """
    Black-Scholes Greeks for any option.
    spot: underlying price. strike: strike price. dte: days to expiry.
    iv: implied vol as decimal (0.30 = 30%). right: C or P.
    qty: optional contracts — adds pos_delta/pos_theta/pos_vega.
    Returns delta, theta, gamma, vega, PoP, intrinsic, extrinsic, itm.
    """
    body = {"spot": spot, "strike": strike, "dte": dte, "iv": iv, "right": right}
    if qty is not None:
        body["qty"] = qty
    return _post("/api/options/greeks", body=body)

@mcp.tool()
def get_vol_analytics(ticker: str) -> dict:
    """
    Volatility analytics: IV skew, term structure, ATM IV ladder.
    Uses live options chain data with quantized-IV detection and BS recalculation.
    Args:
        ticker: Ticker symbol, e.g. "AAPL"
    """
    return _get(f"/api/options/vol-analytics?ticker={ticker}")

@mcp.tool()
def get_position_limits(ticker: str) -> dict:
    """
    Max profit, max loss, and breakeven prices for all open positions in a ticker.
    Returns: max_profit, max_loss, net_premium, breakevens[], spot, legs[].
    Args:
        ticker: Ticker symbol matching an open position, e.g. "MSFT"
    """
    import json as _json
    import urllib.parse as _urlparse
    positions_resp = _get("/api/positions")
    all_positions = positions_resp.get("positions", [])
    ticker_up = ticker.upper()
    legs = [
        {
            "right": p.get("right", "C"),
            "strike": float(p.get("strike", 0)),
            "qty": float(p.get("qty", 0)),
            "premium": float(p.get("avg_cost", 0)) / float(p.get("multiplier", 100) or 100),
            "expiry": p.get("expiry", ""),
        }
        for p in all_positions
        if p.get("ticker", "").upper() == ticker_up and p.get("sec_type") == "OPT"
    ]
    if not legs:
        return {"error": f"No open option positions found for {ticker_up}"}
    legs_json = _urlparse.quote(_json.dumps(legs))
    return _get(f"/api/options/position-limits?ticker={ticker_up}&legs={legs_json}")

@mcp.tool()
def get_forward_pnl(
    ticker: str,
    target_price: float,
    target_date: str,
    iv_multiplier: float = 1.0,
) -> dict:
    """
    Forward P&L of all open positions in a ticker at a target price and date.
    Args:
        ticker:        Ticker symbol matching an open position, e.g. "MSFT"
        target_price:  Hypothetical future spot price, e.g. 450.0
        target_date:   ISO date string, e.g. "2025-07-01"
        iv_multiplier: IV adjustment (default 1.0; use 0.6 for post-earnings IV crush)
    """
    import json as _json
    import urllib.parse as _urlparse
    positions_resp = _get("/api/positions")
    all_positions = positions_resp.get("positions", [])
    ticker_up = ticker.upper()
    legs = [
        {
            "right": p.get("right", "C"),
            "strike": float(p.get("strike", 0)),
            "qty": float(p.get("qty", 0)),
            "premium": float(p.get("avg_cost", 0)) / float(p.get("multiplier", 100) or 100),
            "expiry": p.get("expiry", ""),
        }
        for p in all_positions
        if p.get("ticker", "").upper() == ticker_up and p.get("sec_type") == "OPT"
    ]
    if not legs:
        return {"error": f"No open option positions found for {ticker_up}"}
    legs_json = _urlparse.quote(_json.dumps(legs))
    params = (
        f"?ticker={ticker_up}"
        f"&legs={legs_json}"
        f"&target_price={target_price}"
        f"&target_date={target_date}"
        f"&iv_adj={iv_multiplier}"
    )
    return _get(f"/api/options/forward-pnl{params}")

# ─── P&L ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_pnl() -> dict:
    """
    Current P&L summary from IBKR positions.
    Returns unrealised P&L per position and portfolio totals.
    """
    return _get("/api/pnl")

@mcp.tool()
def get_pnl_history(days: int = 90) -> dict:
    """
    Historical portfolio equity curve from end-of-day snapshots.
    Returns daily net_liquidation, unrealized_pnl, realized_pnl, and
    buying_power for up to `days` trading days (default 90).
    Args:
        days: Number of calendar days of history (default 90, max 365)
    """
    return _get("/api/pnl/history", params={"days": days})

# ─── Portfolio analytics ──────────────────────────────────────────────────────

@mcp.tool()
def get_portfolio_beta() -> dict:
    """
    SPY beta-weighted portfolio delta with per-ticker breakdown.
    Returns beta_weighted_delta, spy_price, and component_betas.
    """
    return _get("/api/portfolio/beta")

@mcp.tool()
def get_sector_exposure() -> dict:
    """
    Portfolio notional exposure grouped by GICS sector.
    Flags breach if any sector exceeds concentration_max_pct (default 40%).
    """
    return _get("/api/portfolio/sector-exposure")

@mcp.tool()
def get_capital_efficiency() -> dict:
    """
    Annualised premium income / capital at risk per position.
    Benchmark is 12% (0.12). Sorted by efficiency descending.
    """
    return _get("/api/portfolio/capital-efficiency")

@mcp.tool()
def get_pcs_exposure() -> dict:
    """
    Portfolio put-call spread (PCS) exposure summary.
    Returns notional exposure, delta contribution, and margin usage.
    """
    return _get("/api/portfolio/pcs-exposure")

@mcp.tool()
def get_earnings_volatility(ticker: str) -> dict:
    """
    Implied earnings move vs historical realized moves for a ticker.
    implied_move_pct = ATM straddle / stock price at nearest post-earnings expiry.
    historical_moves = last 8 earnings realized absolute pct moves.
    Args:
        ticker: Stock ticker e.g. AAPL
    """
    return _get(f"/api/market/earnings-volatility/{ticker.upper()}")

# ─── Scripts & automation ─────────────────────────────────────────────────────

@mcp.tool()
def list_scripts() -> dict:
    """
    List all available automation scripts with keys, names, and last-run timestamps.
    Use before calling run_script() to discover valid script keys.
    """
    return _get("/api/run/scripts")

@mcp.tool()
def run_script(script_key: str) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Execute a named automation script on the Fortress VPS.
    Call list_scripts() first to discover valid script keys.
    Returns stdout, stderr, exit code, and duration.
    Args:
        script_key: Script identifier from list_scripts(), e.g. "premarket"
    """
    _writes_check()
    return _post(f"/api/run/{script_key}")

@mcp.tool()
def refresh_iv_data() -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Trigger a fresh IV crush scan (workflow_05_iv_crush_report.py).

    Use when:
    - IVR values show as 0 or near-zero intraday
    - Morning scan data is stale
    - You need current IV ranks before selecting strikes

    Takes ~15 seconds. Returns ranked candidates with IVR, current IV,
    HV spread, and signals.
    """
    _writes_check()
    return _post("/api/run/iv_crush")

@mcp.tool()
def get_time_of_day() -> dict:
    """
    Current market session context — pre-market, open, after-hours, or closed.
    Returns current time, next open/close, and whether today is a trading day.
    """
    return _get("/api/run/time_of_day")

# ─── Chart & market data ──────────────────────────────────────────────────────

@mcp.tool()
def get_trade_report() -> dict:
    """
    Full structured trade report. More detailed than get_briefing — includes
    per-ticker candidate rows with IV rank, GEX zone, bias badge, action
    recommendations, concentration warnings, stop-loss flags.
    """
    return _get("/api/manage/trade_report")

@mcp.tool()
def get_chart_data(ticker: str, period: str = "6mo", interval: str = "1d") -> dict:
    """
    OHLCV price data plus technical indicators for a ticker.
    Returns candlestick data, 50/200 SMA, RSI(14), MACD(12,26,9),
    Bollinger Bands(20,2), and key GEX/strike overlay levels.
    Args:
        ticker:   Ticker symbol, e.g. "MSFT"
        period:   "1mo", "3mo", "6mo", "1y", "2y" (default "6mo")
        interval: "1d", "1wk" (default "1d")
    """
    params = f"?period={period}&interval={interval}"
    chart  = _get(f"/api/chart/{ticker}{params}")
    levels = _get(f"/api/chart/{ticker}/levels")
    return {"chart": chart, "levels": levels}

@mcp.tool()
def get_order_flow_chart(ticker: str) -> dict:
    """
    Per-ticker options order flow overlay data for the chart view.
    Args:
        ticker: Ticker symbol, e.g. "AAPL"
    """
    return _get(f"/api/chart/{ticker}/order_flow")

# ─── Pre-trade & management ───────────────────────────────────────────────────

@mcp.tool()
def get_pretrade_all() -> dict:
    """
    Pre-trade gate check across every ticker in the universe at once.
    Returns pass/fail verdict per ticker with blocking reason if failed.
    """
    return _get("/api/manage/pretrade_all")

@mcp.tool()
def get_stop_loss_all() -> dict:
    """
    Stop-loss signals for every open position at once.
    Returns hold / close / reduce verdict per position.
    """
    return _get("/api/manage/stop_loss_all")

@mcp.tool()
def get_roll_all() -> dict:
    """
    Roll candidates for every open position at once.
    Returns roll recommendation, urgency, and suggested new strikes/expiry.
    """
    return _get("/api/manage/roll_all")

# ─── Misc read tools ──────────────────────────────────────────────────────────

@mcp.tool()
def get_journal_suggestion() -> dict:
    """
    AI-generated journal entry suggestion based on today's positions and market conditions.
    """
    return _get("/api/journal/suggest")

@mcp.tool()
def get_earnings_history(ticker: str) -> dict:
    """
    Historical earnings dates for a ticker from yfinance.
    Args:
        ticker: Ticker symbol, e.g. "MSFT"
    """
    return _get(f"/api/calendar/{ticker}/history")

@mcp.tool()
def get_settings_narrative() -> dict:
    """
    Plain-English summary of current strategy settings — trader persona,
    active strategies, risk parameters, and signal mode.
    """
    return _get("/api/settings/narrative")

@mcp.tool()
def get_hydrated_assets() -> dict:
    """
    In-memory hydration cache — values pushed by VPS automation scripts.
    Returns all cached asset keys with their values and timestamps.
    """
    return _get("/api/manage/hydrated-assets")

@mcp.tool()
def get_ibkr_preview() -> dict:
    """
    IBKR connection state preview including account summary and margin.
    Read-only — does not place any orders.
    """
    return _get("/api/ibkr/preview")

@mcp.tool()
def get_version() -> dict:
    """
    MCP server version and runtime info.
    """
    return {
        "mcp_version": FORTRESS_MCP_VERSION,
        "api_url": API_URL,
        "tier2_writes_enabled": ALLOW_WRITES,
        "quantdata": "standalone quantdata-mcp server (registered separately)",
    }


# ─── Write tools — order lifecycle ───────────────────────────────────────────

@mcp.tool()
def force_decline_order(order_id: str) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Force-cancel any pending order regardless of status (submitted, staged, stuck).
    Use when normal decline fails (order already sent to IBKR or locked).
    Calls DELETE /api/orders/pending/{id}/force.

    Args:
        order_id: Order UUID from get_pending_orders()
    """
    _writes_check()
    return _delete(f"/api/orders/pending/{order_id}/force")


@mcp.tool()
def expire_stale_orders() -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Bulk-expire all stale DAY-order 'submitted' orders still in the queue.
    Safe to call at EOD — only affects same-day submitted orders that never
    received a fill confirmation.
    Calls POST /api/orders/expire-stale.
    """
    _writes_check()
    return _post("/api/orders/expire-stale")


# ─── yfinance GEX + IV skew ───────────────────────────────────────────────────

@mcp.tool()
def get_gex(ticker: str, max_expiries: int = 6) -> dict:
    """
    Gamma Exposure (GEX) by strike for a ticker, computed via yfinance + Black-Scholes.

    Methodology (dealer-centric):
      GEX = gamma × OI × 100 × spot
      Calls: POSITIVE (dealers long gamma → resistance walls)
      Puts:  NEGATIVE (dealers short gamma → support floors)

    Returns: spot_price, call_wall, put_wall, flip_level, net_gex_total,
             gex_levels[] (all strikes sorted), expirations used, as_of.

    Args:
        ticker:       Uppercase ticker symbol, e.g. 'SPY', 'AAPL'
        max_expiries: Number of near-term expirations to aggregate (default 6)

    PREREQUISITE: options_analytics.py must be deployed and registered in main.py.
    """
    return _get(f"/api/options/gex/{ticker}", params={"max_expiries": max_expiries})


@mcp.tool()
def get_vol_skew(ticker: str, expiry: Optional[str] = None) -> dict:
    """
    IV skew for a ticker: put vs call IV across strikes, delta-weighted skew metrics,
    and ATM term structure. Computed from yfinance options chain.

    Key outputs:
      - skew_25d: put25d_iv - call25d_iv (positive = put skew / fear premium)
      - skew_10d: put10d_iv - call10d_iv (tail skew)
      - term_structure: ATM IV per expiry (first 8 expirations)
      - strikes[]: full chain with call_iv, put_iv, call_delta, put_delta

    Args:
        ticker: Uppercase ticker symbol, e.g. 'SPY', 'MSFT'
        expiry: Expiration date YYYY-MM-DD. Defaults to nearest available.

    PREREQUISITE: options_analytics.py must be deployed and registered in main.py.
    """
    params: dict = {}
    if expiry:
        params["expiry"] = expiry
    return _get(f"/api/options/vol-skew/{ticker}", params=params or None)


@mcp.tool()
def get_strategy_metrics(
    ticker: str,
    mode: str = "new",
    target_dte: int = 45,
) -> dict:
    """
    Multi-strategy comparison for a ticker: PMCC, PCS, CSP, Iron Condor, Diagonal.

    Regime gates are applied first (bullish→PMCC/CSP, neutral→IC, bearish→IC/CSP-far-OTM),
    then strategies are ranked by annualized yield. The top-scoring strategy is marked
    recommended=True.

    Key outputs per strategy:
      - short_name: PMCC | PCS | CSP | IC | Diagonal
      - regime_score: 0-5 (higher = better fit for current regime)
      - annualized_yield: estimated annualized premium yield
      - recommended: True on the best-fit strategy
      - capital_required: estimated buying power usage
      - ivr, regime, earnings_safe included at the top level

    Args:
        ticker:     Uppercase ticker symbol, e.g. 'AAPL', 'SPY'
        mode:       'new' (screening new positions) or 'roll' (evaluating rolls)
        target_dte: Target days-to-expiry for the short leg (default 45)
    """
    return _get("/api/options/strategy_metrics", params={
        "ticker":     ticker,
        "mode":       mode,
        "target_dte": target_dte,
    })


@mcp.tool()
def check_liquidity(
    ticker: str,
    expiry: Optional[str] = None,
    moneyness_range: float = 0.15,
) -> dict:
    """
    Advisory bid-ask spread quality check for a ticker's options chain (yfinance).

    Thresholds (Strategy §4 Quality Filters):
      < 5%:  GOOD — tradeable without advisory
      5-10%: ADVISORY — flag in pre-trade check, but not a hard block
      > 10%: WIDE — hard block per strategy §4

    Key outputs:
      - liquidity_grade: A (≥80% good), B (≥60%), C (≥40%), D (<40%)
      - atm_spread_pct: average spread % at ATM strike
      - atm_advisory: True if ATM spread ≥ 5% (triggers advisory in candidates tab)
      - summary: {total, good, advisory, wide, good_pct}
      - strikes[]: per-strike bid/ask/spread data within moneyness_range of spot

    Args:
        ticker:          Uppercase ticker symbol, e.g. 'SPY', 'AAPL'
        expiry:          Expiry YYYY-MM-DD. Defaults to nearest 21-60 DTE.
        moneyness_range: Strike range from spot to scan (default 0.15 = ±15%)

    PREREQUISITE: options_analytics.py must be deployed and registered in main.py.
    """
    params: dict = {"moneyness_range": moneyness_range}
    if expiry:
        params["expiry"] = expiry
    return _get(f"/api/options/liquidity/{ticker}", params=params)


@mcp.tool()
def get_iv_rank(ticker: str) -> dict:
    """
    IV rank for a ticker — THE canonical IV rank source (replaces quantdata's
    broken iv_rank, whose ticker argument is ignored upstream).

    Backend computes ATM IV by Black-Scholes inversion of yfinance lastPrice
    (Yahoo's impliedVolatility column is placeholder junk on the delayed feed),
    median of the 5 nearest-to-spot traded strikes per side, ~40 DTE monthly
    preferred.

    Key outputs:
      - iv_rank:     0-100. Strategy gates: >=25 required for entry, >=50 prime.
      - current_iv:  ATM IV as percent (e.g. 31.2 = 31.2%)
      - call_iv / put_iv: per-side ATM IV
      - iv_52w_high / iv_52w_low: ranking bounds
      - source: 'hv_proxy' (ranked within 52w realized-vol range — cold start)
                or 'iv_snapshots' (true IV rank from own daily history, >=60 days)
      - n_snapshots: daily IV snapshots collected so far (60 -> true rank)

    Each call snapshots today's IV to data/iv_history.json, so calling this for
    the universe daily (see snapshot_iv.sh) builds toward true IV rank.

    Args:
        ticker: Uppercase ticker symbol, e.g. 'AAPL', 'MSFT'

    PREREQUISITE: options_analytics.py (2026-06-10+) deployed and registered.
    """
    return _get(f"/api/options/iv-rank/{ticker}")


@mcp.tool()
def get_macro_events(defer_days: int = 2) -> dict:
    """
    Macro economic-event calendar for the catalyst gate (Strategy §4 binary-event
    timing). Returns upcoming FOMC/CPI/PPI/NFP/PCE events with days_until and a
    portfolio-level defer_advisory when a HIGH-impact event falls within
    defer_days (default 2). Advisory only — never blocks (§15.1).

    Use in the pre-trade workflow: if defer_advisory is True, hold new
    premium-selling entries until the event clears. Keep the calendar current
    with set_macro_events() sourced from FRED / FMP economics (the backend has
    no macro-data credentials — Claude is the curator).

    defer_days: high-impact proximity window for the defer advisory (0-14).
    """
    return _get("/api/options/macro-events", params={"defer_days": defer_days})


@mcp.tool()
def set_macro_events(events: list[dict]) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Replace the macro-event store that feeds the catalyst gate + Parapet event
    horizon. Curate from FRED (release dates) / FMP economics calendar, then push
    the full forward list here (it replaces, not appends; past events auto-prune).

    events: list of {label, date, impact?, note?} where
        label  — e.g. 'FOMC', 'CPI (May)', 'NFP'
        date   — 'YYYY-MM-DD'
        impact — 'high' | 'medium' | 'low' (optional; auto-classified from the
                 label if omitted — FOMC/CPI/PPI/NFP/PCE → high)
        note   — optional context, e.g. 'Warsh first meeting; hold expected'
    """
    _writes_check()
    return _post("/api/options/macro-events", body={"events": events})


@mcp.tool()
def get_vix_term() -> dict:
    """
    VIX term-structure regime input for premium selling (advisory, §15.1).
    Compares spot VIX vs VIX3M (3-month):
      contango (VIX < VIX3M)      → calm, vol-selling favored
      backwardation (VIX > VIX3M) → stress/term inversion — tighten size or
                                    defer new short premium
    Returns vix, vix3m, ratio, state, signal, premium_selling_favorable.
    A useful complement to the regime score and the catalyst gate.
    """
    return _get("/api/options/vix-term")


@mcp.tool()
def get_trade_outcomes() -> dict:
    """
    Structured closed-trade records + overall summary (win rate, expectancy,
    avg win/loss) for the expectancy feedback loop — the numbers companion to
    the prose journal. For expectancy bucketed by IVR/DTE/short-delta at entry,
    run `journal_analytics.py` over the same store.
    """
    return _get("/api/trade-outcomes")


@mcp.tool()
def log_trade_outcome(
    ticker: str,
    strategy: str,
    realized_pnl: float,
    exit_reason: str,
    ivr_at_entry: Optional[float] = None,
    dte_at_entry: Optional[int] = None,
    short_delta_at_entry: Optional[float] = None,
    days_held: Optional[int] = None,
    opened: Optional[str] = None,
    closed: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]
    Append one CLOSED-trade record to the trade-outcomes store — the numbers
    layer that powers "which setups actually pay?" analysis. Log at every close,
    alongside the prose journal entry.

    Capture the ENTRY conditions so the feedback loop can bucket results:
      ivr_at_entry           — IV rank when the trade was opened
      dte_at_entry           — short-leg DTE at open
      short_delta_at_entry   — short-leg delta at open
    realized_pnl: USD, negative = loss. exit_reason: e.g. 'profit_target_50',
    'rolled', '21dte', 'stop_200sma', 'earnings_close'. opened/closed: 'YYYY-MM-DD'.
    """
    _writes_check()
    body: dict = {
        "ticker": ticker, "strategy": strategy,
        "realized_pnl": realized_pnl, "exit_reason": exit_reason,
    }
    for k, v in (
        ("ivr_at_entry", ivr_at_entry), ("dte_at_entry", dte_at_entry),
        ("short_delta_at_entry", short_delta_at_entry), ("days_held", days_held),
        ("opened", opened), ("closed", closed), ("notes", notes),
    ):
        if v is not None:
            body[k] = v
    return _post("/api/trade-outcomes", body=body)


@mcp.tool()
def get_contract_price(ticker: str, strike: float, expiry: str, right: str = "P") -> dict:
    """
    Live quote for ONE specific option contract at ANY strike — unlike
    check_liquidity, which only covers strikes near spot. IBKR-first (real-time
    bid/ask/last/IV) with a yfinance lastPrice fallback. Use this to price a
    far-OTM hedge or close leg when building a ticket.

    expiry: 'YYYY-MM-DD'. right: 'C' or 'P'. Returns bid/ask/mid/last/iv_pct +
    source. (QuantData's qd_get_contract_price is a good cross-check for
    last-traded prints, but this is the backend-native, real-time source.)
    """
    return _get(f"/api/options/contract-price/{ticker}",
                params={"strike": strike, "expiry": expiry, "right": right})


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not API_TOKEN:
        import sys
        print(
            "ERROR: FORTRESS_API_TOKEN environment variable is not set.\n"
            "Set it to the 64-char token from the VPS systemd override.\n"
            "Example: export FORTRESS_API_TOKEN=07f03fb6...",
            file=sys.stderr,
        )
        sys.exit(1)

    tier2_status = "ENABLED" if ALLOW_WRITES else "DISABLED (set FORTRESS_MCP_ALLOW_WRITES=1 to enable)"
    import sys
    print(f"[fortress-mcp v{FORTRESS_MCP_VERSION}] Connecting to {API_URL}", file=sys.stderr)
    print(f"[fortress-mcp] Tier 2 write tools: {tier2_status}", file=sys.stderr)
    print(f"[fortress-mcp] QuantData: use standalone quantdata-mcp server", file=sys.stderr)

    mcp.run(transport="stdio")
