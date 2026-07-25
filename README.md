# Portfolio Manager

A research workflow for stocks, built around three layers:

1. **Kronos** — an open-source foundation model ([shiyu-coder/Kronos](https://github.com/shiyu-coder/Kronos), MIT)
   trained on 12B+ candlesticks from 45 exchanges. It reads OHLCV price action directly and
   outputs a forward price prediction with a confidence interval.
2. **The Kronos Ledger** — a one-page, newspaper-style HTML tearsheet per ticker: forecast
   chart, technicals dashboard (Bollinger, SMA 50/200, RSI, MACD, ATR, volume), fundamentals
   from SEC EDGAR, a news block, and a transparent rule-based BUY / SELL / HOLD house call.
3. **Claude for fundamentals** — per-ticker Claude Projects grounded only on the company's own
   filings, producing bull-case and bear-case memos you re-check every quarter.

> **Research workflow only. Not financial advice. Stocks carry real risk.**
> The point of this stack is to make you *slower and more grounded*, not faster and more
> impulsive. If you catch yourself using it to chase moves, reset.

## Repo layout

```
.claude/skills/kronos/    Claude skill wrapping Kronos — /kronos AAPL from any conversation
tearsheet/                Kronos Ledger generator + self-contained HTML template
docs/ROUTINE.md           The weekly + quarterly routine that makes the stack a system
watchlist.md              Your 5-10 ticker watchlist and weekly Kronos log
memos/                    Bull/bear memo template + your saved memos per ticker
```

## Quick start

**1. Run a Kronos forecast** (from a Claude Code conversation in this repo, just ask —
"run kronos on AAPL" — or run the script directly):

```bash
python3 .claude/skills/kronos/scripts/run_kronos.py AAPL          # 6mo daily, 24-day forecast
python3 .claude/skills/kronos/scripts/run_kronos.py NVDA 1y 1d 30
python3 .claude/skills/kronos/scripts/run_kronos.py BTC-USD 3mo 4h 48
```

First run auto-installs everything (Kronos repo + venv + torch + model weights, 3-7 min).
Every later run is seconds.

**2. Generate a Ledger tearsheet** for any ticker worth a closer look:

```bash
# capture the forecast as JSON while running the skill
KRONOS_JSON_OUT=forecast.json \
    python3 .claude/skills/kronos/scripts/run_kronos.py NVDA 1y 1d 30

# build the one-page tearsheet (OHLCV + technicals + EDGAR + news + house call)
python3 tearsheet/generate_tearsheet.py NVDA --forecast forecast.json
open tearsheet/output/NVDA.html
```

No network? `python3 tearsheet/generate_tearsheet.py DEMO --demo` renders the full page
with synthetic data so you can see the layout.

**3. Follow the routine** — [docs/ROUTINE.md](docs/ROUTINE.md). The tools only matter on a
schedule: weekly Kronos pass over the watchlist, Ledger for anything flagged, quarterly
memo refresh when the 10-Q drops.

## How to read a Kronos forecast

The confidence interval is the signal nobody explains:

- **NARROW band (< 5%)** — the model is relatively certain. A signal worth investigating.
  Confirm on a second timeframe before giving it any weight.
- **MODERATE band (5–10%)** — context only. Check other timeframes.
- **WIDE band (> 10%)** — the model is hedging. The prediction is noise. Ignore it.

A single prediction on a single timeframe is never a signal — it is a starting point for
further research. Look for the same direction across multiple timeframes.

## Requirements

- Python 3.10+ (the skill creates its own venv on first run)
- Network access to Yahoo Finance (OHLCV + news), HuggingFace (model weights, first run
  only), and SEC EDGAR (fundamentals)
- Before fetching EDGAR data, set your contact email in `EDGAR_UA` at the top of
  `tearsheet/generate_tearsheet.py` — the SEC requires a real contact in the User-Agent

## Credits

- Kronos model: [shiyu-coder/Kronos](https://github.com/shiyu-coder/Kronos) (MIT)
- Claude skill: vendored from
  [coopersimson96/kronos-claude-skill](https://github.com/coopersimson96/kronos-claude-skill)
  with paths adapted for in-repo use and an optional `KRONOS_JSON_OUT` export added
- The Ledger design follows the "Kronos Ledger" tearsheet concept from the SF140 setup guide
