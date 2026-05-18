#!/usr/bin/env python3
"""
examples/morning_scan.py — Fortress MCP: Full Morning Scan
Runs the complete morning workflow in one pass:
  1. Trade report (all candidates + actions for the day)
  2. Bulk pre-trade gate across the universe
  3. Stop-loss verdicts for all open positions
  4. Roll evaluations for all open positions
  5. Time-of-day context

Writes results to morning_scan_output.json.

Usage:
    export FORTRESS_MCP_PATH=/path/to/fortress-mcp/fortress_mcp.py
    export FORTRESS_API_URL=http://YOUR_VPS_IP:3000
    export FORTRESS_API_TOKEN=YOUR_TOKEN
    python3 examples/morning_scan.py
"""
import subprocess
import json
import os
import time

MCP_PATH = os.environ.get(
    "FORTRESS_MCP_PATH",
    os.path.join(os.path.dirname(__file__), "..", "fortress_mcp.py"),
)
env = os.environ.copy()


def call_mcp_tool(tool_name: str, arguments: dict | None = None) -> dict | str | None:
    """Spawn the MCP server as a subprocess, call one tool, return the result."""
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
    time.sleep(3)
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


data: dict = {}

print("── Time of day context ───────────────────────────────────────────────")
data["time_of_day"] = call_mcp_tool("get_time_of_day")
print(json.dumps(data["time_of_day"], indent=2))

print("\n── Trade report ──────────────────────────────────────────────────────")
data["trade_report"] = call_mcp_tool("get_trade_report")
print("  Fetched trade report")

print("\n── Bulk pre-trade gate ───────────────────────────────────────────────")
data["pretrade_all"] = call_mcp_tool("get_pretrade_all")
print("  Fetched pretrade_all")

print("\n── Stop-loss scan (all positions) ────────────────────────────────────")
data["stop_loss_all"] = call_mcp_tool("get_stop_loss_all")
print("  Fetched stop_loss_all")

print("\n── Roll scan (all positions) ─────────────────────────────────────────")
data["roll_all"] = call_mcp_tool("get_roll_all")
print("  Fetched roll_all")

output_path = os.path.join(os.path.dirname(__file__), "morning_scan_output.json")
with open(output_path, "w") as f:
    json.dump(data, f, indent=2)
print(f"\nResults written to {output_path}")

# Print a quick summary
print("\n=== QUICK SUMMARY ===")
if isinstance(data.get("stop_loss_all"), dict):
    closes = [t for t, v in data["stop_loss_all"].items()
              if isinstance(v, dict) and v.get("verdict") == "close"]
    if closes:
        print(f"  ⚠  Close signals: {', '.join(closes)}")
    else:
        print("  ✓  No close signals")

if isinstance(data.get("roll_all"), dict):
    urgent = [t for t, v in data["roll_all"].items()
              if isinstance(v, dict) and v.get("urgency") in ("high", "critical")]
    if urgent:
        print(f"  ⚠  Urgent rolls: {', '.join(urgent)}")
    else:
        print("  ✓  No urgent rolls")
