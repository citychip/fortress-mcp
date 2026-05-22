# Contributing to Fortress MCP

Thank you for your interest in contributing! This guide will help you get started.

---

## Code of Conduct

- Be respectful and constructive
- Focus on what is best for the community
- Show empathy towards other contributors
- Trading systems require precision — accuracy matters

---

## How Can I Contribute?

### Reporting Bugs

**Before submitting:**
- Check existing [GitHub Issues](https://github.com/citychip/fortress-mcp/issues)
- Test with the latest fortress-api backend
- Verify your bearer token is valid

**Bug report should include:**
- Python version (`python3 --version`)
- OS (Mac, Windows, Linux)
- Steps to reproduce
- Expected vs actual behavior
- Claude Desktop logs (check `~/Library/Logs/Claude/mcp*.log` on Mac)
- Error messages from MCP server

### Suggesting New Tools

Tool requests welcome! Include:
- **Use case**: What portfolio/trading question does this answer?
- **Data source**: Is this from fortress-api, quantdata-mcp, or a new source?
- **Parameters**: What inputs does the tool need?
- **Output format**: Plain text, table, JSON?

### Pull Requests

1. Fork the repo and create a feature branch
2. Make your changes following the style guide
3. Test with Claude Desktop
4. Update README if adding tools
5. Submit PR with clear description

---

## Development Setup

### Prerequisites

- Python 3.10+
- Claude Desktop installed
- fortress-api backend running
- Git

### Local Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/fortress-mcp.git
cd fortress-mcp

# Install dependencies
pip install mcp httpx requests

# Copy config snippet
cp claude_desktop_config_snippet.json ~/fortress_mcp_config.json

# Edit with your credentials
nano ~/fortress_mcp_config.json
```

### Testing

**With Claude Desktop:**
1. Add to `claude_desktop_config.json`
2. Restart Claude Desktop
3. Test a tool: "Call get_briefing()"
4. Check MCP logs: `tail -f ~/Library/Logs/Claude/mcp*.log`

**With Python REPL:**
```python
import os
os.environ["FORTRESS_API_URL"] = "http://localhost:3000"
os.environ["FORTRESS_API_TOKEN"] = "your_token"

# Import and test
from fortress_mcp import _get
briefing = _get("/api/briefing")
print(briefing)
```

---

## Project Structure

```
fortress-mcp/
├── fortress_mcp.py                 # Main MCP server (57 tools)
├── qd_mcp_client.py                # QuantData MCP client helper
├── claude_desktop_config_snippet.json  # Config template
├── examples/
│   ├── briefing.py                 # Morning briefing script
│   ├── gex_scan.py                 # GEX wall scanner
│   ├── position_analysis.py        # Position deep-dive
│   ├── forward_pnl_sim.py          # P&L scenario simulator
│   ├── chart_technicals.py         # Chart + indicators
│   ├── vol_analysis.py             # Volatility analytics
│   ├── morning_scan.py             # Pre-market scan
│   ├── full_analysis.py            # Complete ticker analysis
│   └── prompts/
│       └── README.md               # Claude prompt library
└── README.md
```

---

## Adding a New Tool

**Example: Adding a "get_concentration_report" tool**

1. **Define the tool in fortress_mcp.py:**

```python
@mcp.tool()
def get_concentration_report() -> str:
    """
    Get portfolio concentration report — tickers above 15% Net Liq.
    
    Returns formatted table with concentration warnings.
    """
    data = _get("/api/briefing")
    concentration = data.get("concentration", [])
    
    # Format output
    lines = ["Portfolio Concentration Report", ""]
    
    if not concentration:
        return "No concentration warnings."
    
    for item in concentration:
        ticker = item["ticker"]
        pct = item["pct_netliq"] * 100
        flag = item.get("flag", "OK")
        
        emoji = "🔴" if flag == "CRITICAL" else "🟡" if flag == "WARNING" else "🟢"
        lines.append(f"{emoji} {ticker}: {pct:.1f}% of Net Liq ({flag})")
    
    return "\n".join(lines)
```

2. **Update README.md:**

Add to the "Portfolio & Positions" section:

```markdown
| `get_concentration_report()` | Portfolio concentration warnings (tickers > 15% Net Liq) |
```

3. **Test in Claude Desktop:**

Restart Claude Desktop and ask:
> "Get the concentration report"

4. **Add example prompt:**

Update `examples/prompts/README.md`:

```markdown
### Concentration Check
\```
Call get_concentration_report to see which tickers are above 15% of Net Liq.
Flag any with CRITICAL status.
\```
```

5. **Create example script** (optional):

```python
# examples/concentration_check.py
"""
Quick concentration check script.
Usage: python3 examples/concentration_check.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fortress_mcp import _get

def main():
    data = _get("/api/briefing")
    concentration = data.get("concentration", [])
    
    print("Portfolio Concentration Report")
    print("=" * 50)
    
    for item in concentration:
        ticker = item["ticker"]
        pct = item["pct_netliq"] * 100
        flag = item.get("flag", "OK")
        print(f"{ticker:6s} {pct:5.1f}%  [{flag}]")

if __name__ == "__main__":
    main()
```

---

## Adding a QuantData Tool

**Example: Adding "qd_get_volatility_surface"**

1. **Add to fortress_mcp.py:**

```python
@mcp.tool()
def qd_get_volatility_surface(ticker: str = "SPY") -> str:
    """
    Get 3D volatility surface (IV across strikes and expirations).
    
    Args:
        ticker: Stock symbol (default: SPY)
    
    Returns:
        Formatted IV surface table
    """
    # Call QuantData API via qd_mcp_client
    from qd_mcp_client import call_qd_tool
    
    try:
        result = call_qd_tool("qd_get_volatility_skew", {"ticker": ticker})
        # Format and return
        return result.get("text", "No data available")
    except Exception as e:
        return f"Error fetching vol surface: {e}"
```

2. **Document in README:**

```markdown
### QuantData Direct

| Tool | What it does |
|------|-------------|
| `qd_get_volatility_surface(ticker)` | 3D volatility surface across strikes/expirations |
```

3. **Test:**

```
> Get the volatility surface for NVDA
```

---

## Code Style

### Python

- Use **type hints** for all function parameters
- Use **docstrings** with clear descriptions
- Prefer `httpx` for async HTTP calls
- Handle errors gracefully with try/except

**Good:**
```python
@mcp.tool()
def get_example(ticker: str, days: int = 30) -> str:
    """
    Get example data for a ticker.
    
    Args:
        ticker: Stock symbol
        days: Lookback period (default: 30)
    
    Returns:
        Formatted text output
    """
    try:
        data = _get(f"/api/example/{ticker}", params={"days": days})
        return format_output(data)
    except httpx.HTTPError as e:
        return f"Error: {e}"
```

**Avoid:**
```python
def get_example(ticker, days):
    data = _get(f"/api/example/{ticker}")
    return data  # No formatting
```

### Output Formatting

- Use **tables** for multi-row data
- Use **emojis** sparingly (✅ ❌ 🔴 🟡 🟢)
- Keep lines under 80 chars when possible
- Use section headers with blank lines

**Example:**
```
Portfolio Summary
─────────────────

✅ Net Liq: $125,340
✅ Delta: +35.2 (target: +35)
⚠️  Theta: -$82/day (below target)

Top Positions:
  MSFT   32.1%  [WARNING]
  AAPL   18.5%  [OK]
  NVDA   15.2%  [OK]
```

---

## Testing

### Unit Tests (Manual)

Test each tool individually:

```bash
# Set environment
export FORTRESS_API_URL=http://localhost:3000
export FORTRESS_API_TOKEN=your_token

# Run Python REPL
python3

>>> from fortress_mcp import get_briefing
>>> print(get_briefing())
```

### Integration Tests (Claude Desktop)

1. Add tool to claude_desktop_config.json
2. Restart Claude
3. Test each new tool with natural language
4. Verify output format is readable

### Example Scripts

Run example scripts to verify API connectivity:

```bash
python3 examples/briefing.py
python3 examples/gex_scan.py
python3 examples/position_analysis.py
```

---

## Common Issues

### "401 Unauthorized"
- Check bearer token is correct
- Verify fortress-api is running
- Test token with curl: `curl -H "Authorization: Bearer TOKEN" http://localhost:3000/api/health`

### "Connection refused"
- fortress-api not running
- Wrong API URL (check port: 3000 for nginx, 8080 for direct FastAPI)

### "Tool not found in Claude Desktop"
- Restart Claude Desktop fully (Quit, not just close window)
- Check `claude_desktop_config.json` syntax (valid JSON)
- Check MCP logs: `tail -f ~/Library/Logs/Claude/mcp*.log`

### "QuantData tools return errors"
- Set `QUANTDATA_AUTH_TOKEN` and `QUANTDATA_INSTANCE_ID` env vars
- Refresh credentials at v3.quantdata.us
- QuantData has rate limits — retry after a few seconds

---

## Pull Request Checklist

Before submitting:

- [ ] Tool tested with Claude Desktop
- [ ] Docstring added with clear description
- [ ] README.md updated (tool added to table)
- [ ] Example prompt added to examples/prompts/README.md (if applicable)
- [ ] No hardcoded credentials
- [ ] Error handling in place
- [ ] Output is human-readable

---

## Documentation Standards

### Tool Docstrings

```python
@mcp.tool()
def tool_name(param: type = default) -> str:
    """
    One-line summary of what this tool does.
    
    More detailed explanation if needed. Mention any important
    behavior, edge cases, or strategy references (§section).
    
    Args:
        param: Description of parameter
    
    Returns:
        Description of return value format
    """
```

### README Updates

When adding a tool, update the appropriate section:

- Portfolio tools → "Portfolio & Positions"
- Market data → "Market Intelligence"
- Strategy checks → "Risk Evaluation"
- QuantData → "QuantData Direct"

Use consistent formatting:

```markdown
| `tool_name(param)` | Brief description |
```

---

## Release Process

Releases follow semantic versioning aligned with fortress-api sprints:

- **v7.1**: Current (57 tools, Sprint v7.1)
- **v7.2**: Next minor (new tools, improvements)
- **v8.0**: Major (breaking changes)

---

## Questions?

- **GitHub Issues**: https://github.com/citychip/fortress-mcp/issues
- **Discussions**: https://github.com/citychip/fortress-mcp/discussions
- **Email**: zzulanas@gmail.com (security issues only)

---

## Thank You!

Every contribution makes Fortress better for the community. Whether it's a bug report, new tool, or improved docs — thank you! 🚀
