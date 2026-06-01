"""
Fortress MCP patch — add to fortress_mcp.py on Windows.

Two new tools:
  1. stage_order      — create a pending order in the Build Center queue
  2. refresh_iv_data  — trigger a fresh IV scan via the iv_crush workflow

HOW TO APPLY:
  Open C:\Users\cityc.000\fortress_mcp\fortress_mcp.py
  Find the section where other tools are defined (look for preview_order or approve_order).
  Paste BOTH functions below into the same class or module.
  Restart Claude Desktop to reload the MCP server.
"""

# ─── TOOL 1: stage_order ─────────────────────────────────────────────────────
# Wraps POST /api/orders/pending
# Places a structured order into the Build Center approval queue.
# After staging, use preview_order(order_id) then approve_order(order_id).

@mcp.tool()
def stage_order(
    ticker: str,
    strategy: str,
    legs: list[dict],
    quantity: int = 1,
    order_type: str = "LMT",
    limit_price: float | None = None,
    notes: str | None = None,
    pop: float | None = None,
    max_profit: float | None = None,
    max_loss: float | None = None,
) -> dict:
    """
    Stage a new order in the Fortress Build Center approval queue.

    Args:
        ticker:      Primary underlying, e.g. "MSFT"
        strategy:    Strategy label, e.g. "PMCC", "CSP", "IC", "PCS"
        legs:        List of leg dicts. Each leg must have:
                       ticker, sec_type ("OPT"|"STK"), right ("C"|"P"),
                       strike (float), expiry ("YYYYMMDD"), action ("BUY"|"SELL"),
                       ratio (int, default 1), exchange (default "CBOE")
                     Example leg:
                       {"ticker": "MSFT", "sec_type": "OPT", "right": "C",
                        "strike": 490.0, "expiry": "20260821",
                        "action": "SELL", "ratio": 1}
        quantity:    Number of contracts (default 1)
        order_type:  "LMT" (default), "MKT", or "MOC"
        limit_price: Limit price per contract (required for LMT orders)
        notes:       Optional rationale / trade notes
        pop:         Probability of profit estimate (0–1)
        max_profit:  Max profit in USD
        max_loss:    Max loss in USD (use negative for debit)

    Returns:
        dict with order id, status, and full order details.
        Use the returned id with preview_order() and approve_order().
    """
    import requests, os

    base_url = os.environ.get("FORTRESS_API_URL", "http://localhost:8081")
    token = os.environ.get("FORTRESS_MCP_TOKEN", "")

    payload = {
        "ticker": ticker.upper(),
        "strategy": strategy,
        "legs": legs,
        "quantity": quantity,
        "order_type": order_type,
        "action": "SELL",  # default; overridden per-leg
        "limit_price": limit_price,
        "notes": notes,
        "submitted_by": "MCP",
        "pop": pop,
        "max_profit": max_profit,
        "max_loss": max_loss,
    }

    resp = requests.post(
        f"{base_url}/api/orders/pending",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=15,
        verify=False,
    )
    resp.raise_for_status()
    data = resp.json()
    order_id = data.get("id", "unknown")
    return {
        "ok": True,
        "order_id": order_id,
        "status": data.get("status", "pending"),
        "message": f"Order staged. Use preview_order('{order_id}') to check margin, then approve_order('{order_id}') to submit.",
        "order": data,
    }


# ─── TOOL 2: refresh_iv_data ─────────────────────────────────────────────────
# Triggers a fresh IV crush scan via the iv_crush workflow script.
# Use when QuantData IV data looks stale or returns zeros intraday.

@mcp.tool()
def refresh_iv_data() -> dict:
    """
    Trigger a fresh IV data scan by running the iv_crush workflow.

    Use this when:
    - The morning IV scan data looks stale
    - IVR values are showing as 0 or near-zero intraday
    - You want up-to-date IV rank before selecting strikes

    The scan takes ~30 seconds. Returns immediately with a job id;
    the data will be updated in the background.
    """
    import requests, os

    base_url = os.environ.get("FORTRESS_API_URL", "http://localhost:8081")
    token = os.environ.get("FORTRESS_MCP_TOKEN", "")

    resp = requests.post(
        f"{base_url}/api/scripts/run",
        json={"key": "iv_crush"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=10,
        verify=False,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "ok": True,
        "message": "IV crush scan triggered. Data will refresh in ~30 seconds.",
        "job": data,
    }
