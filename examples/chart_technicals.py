#!/usr/bin/env python3
"""
examples/chart_technicals.py — Fortress MCP: Chart Data + Order Flow
Fetches OHLCV + technicals (SMA/RSI/MACD/BB) and order flow data for a
list of tickers. Prints a quick technical summary table and writes full
data to chart_technicals_output.json.

Usage:
    export FORTRESS_MCP_PATH=/path/to/fortress-mcp/fortress_mcp.py
    export FORTRESS_API_URL=http://YOUR_VPS_IP:3000
    export FORTRESS_API_TOKEN=YOUR_TOKEN
    python3 examples/chart_technicals.py [TICKER1 TICKER2 ...]
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


def extract_latest(chart_data: dict) -> dict:
    """Pull the most recent bar's indicators from chart data."""
    out = {}
    try:
        candles = chart_data.get("chart", {}).get("candles", [])
        if candles:
            last = candles[-1]
            out["close"] = last.get("close")
            out["rsi"] = last.get("rsi")
            out["sma50"] = last.get("sma50")
            out["sma200"] = last.get("sma200")
            out["macd"] = last.get("macd")
            out["macd_signal"] = last.get("macd_signal")
    except Exception:
        pass
    return out


tickers = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_TICKERS
results: dict = {}

print(f"\n{'Ticker':<8} {'Close':>8} {'RSI':>6} {'vs SMA50':>9} {'vs SMA200':>10} {'MACD':>8}")
print("─" * 55)

for ticker in tickers:
    entry: dict = {}

    entry["chart"] = call_mcp_tool("get_chart_data", {"ticker": ticker, "period": "6mo"})
    entry["order_flow"] = call_mcp_tool("get_order_flow_chart", {"ticker": ticker})
    results[ticker] = entry

    ind = extract_latest(entry)
    close = ind.get("close", 0) or 0
    rsi = ind.get("rsi")
    sma50 = ind.get("sma50")
    sma200 = ind.get("sma200")
    macd = ind.get("macd")

    vs50 = f"{((close / sma50) - 1) * 100:+.1f}%" if sma50 else "n/a"
    vs200 = f"{((close / sma200) - 1) * 100:+.1f}%" if sma200 else "n/a"
    rsi_str = f"{rsi:.1f}" if rsi else "n/a"
    macd_str = f"{macd:+.2f}" if macd is not None else "n/a"

    print(f"{ticker:<8} {close:>8.2f} {rsi_str:>6} {vs50:>9} {vs200:>10} {macd_str:>8}")

output_path = os.path.join(os.path.dirname(__file__), "chart_technicals_output.json")
with open(output_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nFull data written to {output_path}")
