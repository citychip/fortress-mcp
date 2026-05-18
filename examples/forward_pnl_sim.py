#!/usr/bin/env python3
"""
examples/forward_pnl_sim.py — Fortress MCP: Forward P&L Simulation
Runs Black-Scholes forward P&L simulations for open positions across
multiple price targets and IV scenarios (base, IV crush, IV expansion).

Usage:
    export FORTRESS_MCP_PATH=/path/to/fortress-mcp/fortress_mcp.py
    export FORTRESS_API_URL=http://YOUR_VPS_IP:3000
    export FORTRESS_API_TOKEN=YOUR_TOKEN
    python3 examples/forward_pnl_sim.py

Edit SCENARIOS below to match your positions and hypotheses.
"""
import subprocess
import json
import os
import time
from datetime import date, timedelta

MCP_PATH = os.environ.get(
    "FORTRESS_MCP_PATH",
    os.path.join(os.path.dirname(__file__), "..", "fortress_mcp.py"),
)
env = os.environ.copy()

# ── Edit these to match your positions and hypotheses ─────────────────────────
SCENARIOS = [
    {
        "ticker": "MSFT",
        "label": "MSFT — bull case (earnings beat)",
        "target_price": 450.0,
        "target_date": (date.today() + timedelta(days=30)).isoformat(),
        "iv_multiplier": 0.6,   # 40% IV crush post-earnings
    },
    {
        "ticker": "MSFT",
        "label": "MSFT — base case (drift to target)",
        "target_price": 430.0,
        "target_date": (date.today() + timedelta(days=45)).isoformat(),
        "iv_multiplier": 1.0,
    },
    {
        "ticker": "MSFT",
        "label": "MSFT — bear case (pullback)",
        "target_price": 400.0,
        "target_date": (date.today() + timedelta(days=20)).isoformat(),
        "iv_multiplier": 1.4,   # IV expansion on selloff
    },
    {
        "ticker": "AVGO",
        "label": "AVGO — earnings IV crush",
        "target_price": 220.0,
        "target_date": (date.today() + timedelta(days=14)).isoformat(),
        "iv_multiplier": 0.55,
    },
]
# ─────────────────────────────────────────────────────────────────────────────


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


results = []
print(f"{'Label':<45} {'Target':>8} {'Date':>12} {'IV×':>5} {'P&L':>10}")
print("─" * 85)

for s in SCENARIOS:
    result = call_mcp_tool("get_forward_pnl", {
        "ticker": s["ticker"],
        "target_price": s["target_price"],
        "target_date": s["target_date"],
        "iv_multiplier": s["iv_multiplier"],
    })
    pnl = None
    if isinstance(result, dict):
        pnl = result.get("point_estimate")
    pnl_str = f"${pnl:+,.0f}" if pnl is not None else "n/a"
    print(f"{s['label']:<45} {s['target_price']:>8.2f} {s['target_date']:>12} {s['iv_multiplier']:>5.2f} {pnl_str:>10}")
    results.append({**s, "result": result})

output_path = os.path.join(os.path.dirname(__file__), "forward_pnl_output.json")
with open(output_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nFull results written to {output_path}")
