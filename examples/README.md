# Fortress MCP — Claude Prompt Library

Ready-to-paste prompts for Claude Desktop with the Fortress MCP connected.
Each prompt is self-contained — paste it directly into a new Claude conversation.

**Updated:** Sprint v7.1 (May 18, 2026) — Strategy v3.7

---

## Morning Workflow

### Full Morning Brief
```
Use get_briefing to fetch today's Fortress briefing, then use get_trade_report
to get the full candidate list. Summarise:
1. The top 3 actionable candidates with their bias, IV rank, and recommended action
2. Any open positions with stop-loss or roll flags
3. Key market context (SPY bias, VIX level, macro notes)
Keep the summary under 300 words and use a table for the candidates.
```

### Morning Scan with Bulk Checks
```
Run a complete morning scan:
1. Call get_time_of_day to confirm market session
2. Call get_pretrade_all to check which universe tickers pass the entry gate today
3. Call get_stop_loss_all to check for any close signals on open positions
4. Call get_roll_all to check for any urgent roll candidates

Present the results as three sections: (a) tickers cleared for entry today,
(b) positions needing attention (close or reduce), (c) positions to consider rolling.
Flag anything that needs immediate action.
```

---

## Position Management

### Full Position Review
```
Review all open positions:
1. Call get_positions to get the current portfolio
2. For each position, call get_position_limits to get max profit, max loss, and breakevens
3. Call get_stop_loss_all and get_roll_all for bulk verdicts

Present a table with: Ticker | Strategy | Max Profit | Max Loss | Breakeven(s) |
Stop-Loss Verdict | Roll Verdict. Highlight any positions within 2% of a breakeven
or with a close/urgent-roll signal.
```

### Scenario Analysis for a Specific Position
```
Run a scenario analysis for my [TICKER] position:
1. Call get_position_limits to get the structural limits and current breakevens
2. Call get_forward_pnl three times with these scenarios:
   - Bull case: target_price=[BULL_PRICE], target_date=[DATE], iv_multiplier=0.6
   - Base case: target_price=[BASE_PRICE], target_date=[DATE], iv_multiplier=1.0
   - Bear case: target_price=[BEAR_PRICE], target_date=[DATE], iv_multiplier=1.3
3. Call get_vol_analytics to check the current IV skew and term structure

Present a scenario table and explain which scenario is most likely given the
current vol surface and chart context.
```

### Post-Earnings Position Review
```
My [TICKER] just reported earnings. Analyse the position:
1. Call get_positions to see the current [TICKER] position details
2. Call get_forward_pnl with iv_multiplier=0.55 (IV crush) and today's close as target_price
3. Call evaluate_post_earnings for the playbook recommendation
4. Call get_vol_analytics to see how the term structure has shifted
5. Call get_chart_data to see the price reaction

Recommend whether to hold, close, or adjust the position given the IV crush
and price move. Show the updated P&L estimate after IV crush.
```

---

## Volatility Analysis

### IV Rank Scan
```
Run an IV rank scan across my universe:
1. Call get_universe to get all tickers
2. For each ticker in Tier 1, call qd_get_iv_rank
3. Sort by IV rank descending

Present a table: Ticker | IV Rank | IV% | Tier. Highlight tickers with IV rank
above 50 as elevated (good for premium selling) and below 20 as suppressed.
```

### Deep Vol Analysis for a Ticker
```
Run a deep volatility analysis for [TICKER]:
1. Call get_vol_analytics to get the IV skew, term structure, and ATM IV ladder
2. Call qd_get_iv_rank for the current IV rank and percentile
3. Call get_chart_data to see the price trend context

Interpret the vol surface: Is the skew steep or flat? Is the term structure
in contango or backwardation? What does this suggest about market expectations?
Is the current IV rank a good entry point for premium selling?
```

### Pre-Earnings Vol Setup
```
Analyse the pre-earnings vol setup for [TICKER] with earnings in [N] days:
1. Call get_vol_analytics to see the current term structure and front-month IV
2. Call qd_get_iv_rank for IV rank context
3. Call get_earnings_history to see historical earnings date patterns
4. Call get_chart_data to see the current technical setup

Estimate the implied earnings move (from front-month ATM IV), compare it to
historical moves, and recommend whether to sell premium into earnings or wait.
```

---

## Trade Research

### Candidate Deep Dive
```
Do a deep dive on [TICKER] as a new trade candidate:
1. Call get_candidates to see if it's already in the screened list
2. Call pretrade_check with ticker=[TICKER] and strategy=pmcc
3. Call get_chart_data with period=6mo to see the technical setup
4. Call get_dp_floors_and_gex to see the GEX walls and DP floors
5. Call qd_get_iv_rank for IV context
6. Call get_vol_analytics for the vol surface

Give a structured trade brief: technical setup, vol context, GEX levels,
pre-trade gate result, and a specific PMCC structure recommendation if the
setup is valid (long strike, short strike, expiry, target premium).
```

### Universe Review
```
Review the current Fortress universe:
1. Call get_universe to see all tickers by tier
2. Call get_candidates to see which ones are currently screened as actionable
3. Call get_market_intelligence to get the current market context

For each Tier 1 ticker not currently in the candidates list, briefly explain
why it might not be passing the screen today. Suggest any tickers that look
close to triggering a signal.
```

---

## Risk & Portfolio

### Portfolio Risk Check
```
Run a full portfolio risk check:
1. Call get_positions to get all open positions
2. Call get_pnl for the current unrealised P&L summary
3. Call get_stop_loss_all for stop-loss verdicts
4. Call get_spy_hedge_coverage to check portfolio hedge status
5. Call get_briefing for the current market bias

Assess: (a) total portfolio delta exposure, (b) any positions with unrealised
loss exceeding 20% of max loss, (c) hedge coverage adequacy given current
market bias. Flag any immediate risk management actions needed.
```

### Journal Entry
```
Help me write a journal entry for today's session:
1. Call get_journal_suggestion for an AI-drafted entry
2. Call get_briefing for today's market context
3. Call get_pnl for today's P&L

Review the suggestion and enhance it with: the key decision made today,
what worked, what didn't, and one lesson to carry forward. Keep it under
200 words and in the first person.
```

---

## Settings & Configuration

### Settings Review
```
Review my current Fortress configuration:
1. Call get_settings_narrative for a plain-English summary
2. Call get_settings to get the full settings JSON

Identify any settings that seem inconsistent with a PMCC-focused strategy.
Suggest any adjustments to risk parameters, signal thresholds, or universe
composition that would improve signal quality.
```

### Script Inventory
```
Show me all available Fortress automation scripts:
1. Call list_scripts to get the full script inventory
2. Call get_time_of_day to see the current market session

For each script, explain when it should be run and what it does. Group them
by: morning scripts, intraday scripts, end-of-day scripts, and maintenance scripts.
```

---

## QuantData Diagnostics

### QuantData Health Check
```
Check the health of my QuantData integration:
1. Call get_settings to see if use_quantdata is enabled
2. Call qd_get_iv_rank with ticker=SPY to test live connectivity
3. Call get_market_intelligence to see if GEX/DP data is populating

If qd_get_iv_rank returns an error or empty data, my QuantData session
credentials have likely expired. Remind me to go to Settings → QuantData
Credentials in the dashboard and refresh my auth_token and cookie values
from a fresh QuantData login session.
```

### Market Intelligence Deep Dive
```
Run a full market intelligence analysis for [TICKER]:
1. Call get_market_intelligence with the ticker to get GEX walls, DP floors,
   net drift, order flow, and regime score
2. Call qd_get_dark_pool_levels for the raw DP level data
3. Call qd_get_net_drift for the cumulative premium flow
4. Call get_chart_data to see the price in context of these levels

Explain: (a) where the key support/resistance levels are based on GEX and DP,
(b) what the net drift and order flow suggest about directional bias,
(c) whether the current regime score supports entering a new position.
```
