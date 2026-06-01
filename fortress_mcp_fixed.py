"""
fortress_mcp_fixed.py — CORRECTED replacement for fortress_mcp.py

TWO BUGS FIXED vs the version you applied:
1. Tools were pasted AFTER mcp.run() — they never registered. Moved before it.
2. stage_order and refresh_iv_data used `requests` + wrong token var.
   Replaced with the file's existing _post() / _writes_check() helpers.

HOW TO APPLY:
  Replace C:\Users\cityc.000\fortress_mcp\fortress_mcp.py with this file
  (rename it to fortress_mcp.py), then restart Claude Desktop.

  OR: open your current fortress_mcp.py and:
  1. DELETE everything from line 1175 to the end (the two pasted tools + trailing blank)
  2. INSERT the two corrected tool definitions below BEFORE the
     `if __name__ == "__main__":` block (around line 1153)
  3. Restart Claude Desktop
"""

# ── Paste these two functions into fortress_mcp.py
# ── BEFORE the `if __name__ == "__main__":` block
# ── (around line 1153, after the qd_status function)

# ─────────────────────────────────────────────────────────────────────────────

# @mcp.tool()
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
    Stage a new order in the Fortress Build Center approval queue.
    [WRITE — requires FORTRESS_MCP_ALLOW_WRITES=1]

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

    Returns:
        dict with order_id, status, and message.
        Next: preview_order(order_id) → approve_order(order_id)
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


# @mcp.tool()
def refresh_iv_data() -> dict:
    """
    Trigger a fresh IV crush scan (workflow_05_iv_crush_report.py).

    Use when:
    - IVR values show as 0 or near-zero intraday
    - Morning scan data is stale
    - You need current IV ranks before selecting strikes

    Takes ~15 seconds. Returns stdout from the scan including
    ranked candidates with IVR, current IV, HV spread, and signals.
    """
    _writes_check()
    return _post("/api/run/iv_crush")


# ─────────────────────────────────────────────────────────────────────────────
# END OF PATCH
# The two functions above replace the broken versions at the bottom of the file.
# Remember to add @mcp.tool() decorator before each def when pasting.
