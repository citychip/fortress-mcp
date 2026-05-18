#!/usr/bin/env python3
"""
examples/vol_analysis.py — Fortress MCP: Volatility Analysis
For each ticker, fetches:
  - IV rank and IV percentile from QuantData
  - Full vol analytics (IV skew, term structure, ATM IV ladder)
  - Position limits (max profit, max loss, breakevens) if a position is open

Writes results to vol_analysis_output.json.

Usage:
    export FORTRESS_MCP_PATH=/path/to/fortress-mcp/fortress_mcp.py
    export FORTRESS_API_URL=http://YOUR_VPS_IP:3000
    export FORTRESS_API_TOKEN=YOUR_TOKEN
    python3 examples/vol_analysis.py [TICKER1 TICKER2 ...]

    # Default tickers if none provided:
    python3 examples/vol_analysis.py MSFT AAPL NVDA
"""
import subprocess
import json
import os
import sys
import time

MCP_PATH = os.environ.get(
    "FORTRESS_MCP_PATH",
    os.path.join(os.path.dirname(__file__), "..", "fortress_mcp.py"),
)
env = os.environ.copy()

DEFAULT_TICKERS = ["MSFT", "AAPL", "NVDA", "AVGO", "META"]


def call_mcp_tool(tool_name: str, arguments: dict | None = None) -> dict | str | None:
    if arguments is None:
        arguments = {}
    proc = subprocess.Popen(
        ["python3", MCP_PATH],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    messages = [
        json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "example-script", "version": "1.0"},
            },
        }) + "\n",
        json.dumps({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }) + "\n",
    ]
    for msg in messages:
        proc.stdin.write(msg.encode())
    proc.stdin.flush()
    time.sleep(4)
    proc.terminate()
    out = proc.stdout.read().decode()
    for line in out.strip().split("\n"):
        if not line.strip():
            continue
        try:
            d = json.loads(line)
            if d.get("id") == 2:
                content = d.get("result", {}).get("content", [])
                if content:
                    text = content[0].get("text", "")
                    try:
                        return json.loads(text)
                    except Exception:
                        return text
        except Exception:
            pass
    return None


tickers = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_TICKERS
results: dict = {}

for ticker in tickers:
    print(f"\n── {ticker} ──────────────────────────────────────────────────────")
    entry: dict = {}

    print(f"  qd_get_iv_rank {ticker}...")
    entry["iv_rank"] = call_mcp_tool("qd_get_iv_rank", {"ticker": ticker})

    print(f"  get_vol_analytics {ticker}...")
    entry["vol_analytics"] = call_mcp_tool("get_vol_analytics", {"ticker": ticker})

    print(f"  get_position_limits {ticker}...")
    entry["position_limits"] = call_mcp_tool("get_position_limits", {"ticker": ticker})

    results[ticker] = entry

    # Quick print
    if isinstance(entry.get("iv_rank"), dict):
        iv = entry["iv_rank"]
        print(f"  IV Rank: {iv.get('iv_rank', 'n/a')}  |  IV%: {iv.get('iv_percentile', 'n/a')}")

    if isinstance(entry.get("position_limits"), dict):
        pl = entry["position_limits"]
        print(f"  Max Profit: {pl.get('max_profit', 'n/a')}  |  Max Loss: {pl.get('max_loss', 'n/a')}")
        be = pl.get("breakevens", [])
        if be:
            print(f"  Breakevens: {', '.join(str(b) for b in be)}")

output_path = os.path.join(os.path.dirname(__file__), "vol_analysis_output.json")
with open(output_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nResults written to {output_path}")
