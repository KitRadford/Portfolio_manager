# The Kronos Ledger

Turns the Kronos skill's raw forecast into a one-page, newspaper-style tearsheet you can
scan in 60 seconds: forecast chart up top, technicals dashboard below (Bollinger 20/2σ,
SMA 50, SMA 200, RSI 14, MACD 12/26/9, ATR 14, volume), fundamentals pulled live from SEC
EDGAR (latest 10-K and 10-Q), a news block, and a top-line BUY / SELL / HOLD house call
with the rule score and reasoning underneath.

The output is a single self-contained HTML file — no external requests, works offline,
light and dark theme, printable.

## Usage

```bash
# 1. Run the Kronos skill with JSON export
KRONOS_JSON_OUT=forecast.json \
    python3 .claude/skills/kronos/scripts/run_kronos.py NVDA 1y 1d 30

# 2. Build the tearsheet
python3 tearsheet/generate_tearsheet.py NVDA --forecast forecast.json

# 3. Open it
open tearsheet/output/NVDA.html
```

Options:

- `--period` / `--interval` — OHLCV history to chart (defaults `1y` / `1d`)
- `--forecast <file>` — the KRONOS_JSON_OUT file; omit and the sheet renders without a
  forecast (the house call then says it is technicals-only)
- `--demo` — fully offline synthetic data, for checking the layout
- `--out <path>` — output location (default `tearsheet/output/<TICKER>.html`)

Dependencies: `yfinance` (already in the skill's requirements) for prices and news; SEC
EDGAR is plain HTTPS. The SEC requires a contact email in the User-Agent header — it is
set in `EDGAR_UA` at the top of the script.

## The house call

A deliberately transparent rule score, printed with its reasoning so you can disagree
with it:

- trend: price vs SMA 200 (±1), SMA 50 vs SMA 200 (±1)
- momentum: RSI overbought/oversold (∓1), MACD histogram sign (±1)
- Kronos: direction worth ±2 when the band is NARROW, ±1 when MODERATE, **zero when WIDE**
  (a wide band is noise by the interval rule)
- score ≥ +3 → BUY · score ≤ −2 → SELL · otherwise HOLD

It is an input to your process, not advice.

## Deploying

The output file is static — host it anywhere (`vercel --prod`, GitHub Pages, or just
share the file). Generated sheets in `tearsheet/output/` are git-ignored.
