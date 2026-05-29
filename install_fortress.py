"""
install_fortress.py — Fortress Dashboard MCP installer

Installs Python dependencies and writes the MCP server config to
Claude Desktop's claude_desktop_config.json automatically.

Supports both:
  - Traditional Claude Desktop install (%APPDATA%\Claude\)
  - UWP (Microsoft Store) Claude install (LocalCache\Roaming\Claude\)

Usage:
    python install_fortress.py

After running, fully quit Claude from the system tray and relaunch.
"""
import json, os, shutil, subprocess, sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
# Update SERVER_PATH if fortress_mcp.py lives somewhere else on your machine.
# On Windows it runs directly; on WSL you can use the WSL path below instead.
SERVER_PATH = str(Path(__file__).resolve())   # same folder as this script

ENTRY = {
    "command": "python",
    "args": [SERVER_PATH],
    "env": {
        "FORTRESS_API_URL": "http://localhost:8081",
        "FORTRESS_API_TOKEN": "PASTE_YOUR_FULL_64_CHAR_TOKEN_HERE",
        "FORTRESS_MCP_ALLOW_WRITES": "1",
    },
}

# ── Find Python ───────────────────────────────────────────────────────────────
def pick_python():
    for c in ("python", "py", "python3"):
        try:
            if subprocess.run([c, "--version"], capture_output=True, timeout=5).returncode == 0:
                return c
        except Exception:
            pass
    return "python"

# ── Find Claude config path (UWP or traditional) ─────────────────────────────
def find_claude_config() -> Path:
    local = os.environ.get("LOCALAPPDATA", "")
    appdata = os.environ.get("APPDATA", "")
    candidates = [
        # UWP / Microsoft Store install
        Path(local) / "Packages" / "Claude_pzs8sxrjxfjjc" / "LocalCache" / "Roaming" / "Claude" / "claude_desktop_config.json",
        # Traditional desktop install
        Path(appdata) / "Claude" / "claude_desktop_config.json",
    ]
    for p in candidates:
        if p.exists():
            print(f"  Found existing config: {p}")
            return p
    # Neither exists — default to UWP path and create it
    print(f"  No existing config found, will create: {candidates[0]}")
    return candidates[0]

# ── Main ──────────────────────────────────────────────────────────────────────
py = pick_python()
print(f"[1/3] Python: {py}")

print(f"[2/3] Installing dependencies...")
result = subprocess.run(
    [py, "-m", "pip", "install", "--upgrade", "mcp", "httpx", "requests"],
    capture_output=True, text=True
)
if result.returncode != 0:
    print(result.stderr)
    sys.exit("pip install failed")
print("      mcp, httpx, requests — OK")

cfg_path = find_claude_config()
cfg_path.parent.mkdir(parents=True, exist_ok=True)

cfg = {}
if cfg_path.exists() and cfg_path.stat().st_size:
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        assert isinstance(cfg, dict)
    except Exception as e:
        bak = cfg_path.with_suffix(".json.bak")
        shutil.copy2(cfg_path, bak)
        print(f"  Existing config unparseable ({e}); backed up to {bak}")
        cfg = {}

servers = cfg.setdefault("mcpServers", {})
if not isinstance(servers, dict):
    sys.exit("Existing 'mcpServers' is not an object — aborting.")

entry = dict(ENTRY)
entry["command"] = py
entry["args"] = [SERVER_PATH]
servers["fortress-dashboard"] = entry

cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

print(f"[3/3] Config written to:\n      {cfg_path}")
print()
print("Done.")
print(f"  Server: {SERVER_PATH}")
print(f"  URL:    {ENTRY['env']['FORTRESS_API_URL']}")
print(f"  Token:  {ENTRY['env']['FORTRESS_API_TOKEN']}")
print(f"  Python: {py}")
print()
print("IMPORTANT: Set FORTRESS_API_TOKEN in claude_desktop_config.json")
print("           to your actual bearer token before restarting Claude.")
print()
print("Next: fully quit Claude from the system tray icon and relaunch.")
