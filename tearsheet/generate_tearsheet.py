#!/usr/bin/env python3
"""Kronos Ledger tearsheet generator.

Builds a one-page, self-contained, newspaper-style HTML tearsheet for a ticker:
forecast chart (from the Kronos skill's JSON export), technicals dashboard
(Bollinger, SMA 50/200, RSI, MACD, ATR, volume), fundamentals from SEC EDGAR,
a news block, and a rule-based BUY / SELL / HOLD house call with its reasoning.

Usage:
    python3 tearsheet/generate_tearsheet.py AAPL
    python3 tearsheet/generate_tearsheet.py NVDA --period 1y --forecast forecast.json
    python3 tearsheet/generate_tearsheet.py DEMO --demo          # offline sample data

To produce the forecast JSON, run the Kronos skill with KRONOS_JSON_OUT set:
    KRONOS_JSON_OUT=forecast.json \
        python3 .claude/skills/kronos/scripts/run_kronos.py NVDA 1y 1d 30

Research workflow only. Not financial advice.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template.html"
OUTPUT_DIR = HERE / "output"
DATA_PLACEHOLDER = "__TEARSHEET_DATA__"

EDGAR_UA = "PortfolioManager research tearsheet (contact: set-your-email@example.com)"

# XBRL tags tried in order until one has data. Companies differ in which they file.
EDGAR_CONCEPTS = {
    "Revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
                "SalesRevenueNet"],
    "Net income": ["NetIncomeLoss"],
    "Diluted EPS": ["EarningsPerShareDiluted", "EarningsPerShareBasic"],
    "Cash & equivalents": ["CashAndCashEquivalentsAtCarryingValue"],
    "Total assets": ["Assets"],
    "Total liabilities": ["Liabilities"],
    "Stockholders equity": ["StockholdersEquity"],
}


def log(msg: str) -> None:
    print(f"[ledger] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- OHLCV

def fetch_ohlcv(ticker: str, period: str, interval: str) -> list[dict]:
    import yfinance as yf

    log(f"fetching {ticker} ({period} of {interval} candles) from yfinance...")
    data = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
    if data.empty:
        raise SystemExit(f"No data for {ticker} period={period} interval={interval}.")
    rows = []
    for ts, row in data.iterrows():
        rows.append({
            "t": ts.strftime("%Y-%m-%d"),
            "open": float(row["Open"]), "high": float(row["High"]),
            "low": float(row["Low"]), "close": float(row["Close"]),
            "volume": float(row["Volume"]),
        })
    return rows


def demo_ohlcv(n: int = 260, seed: int = 140, start_price: float = 120.0) -> list[dict]:
    """Deterministic synthetic daily candles (no network, no RNG module state)."""
    rows = []
    price = start_price
    day = datetime(2025, 7, 21)
    state = seed
    for i in range(n):
        # xorshift-ish deterministic pseudo-randoms in [0, 1)
        state = (state * 48271) % 2147483647
        r1 = state / 2147483647
        state = (state * 48271) % 2147483647
        r2 = state / 2147483647
        drift = 0.0006 + 0.0004 * math.sin(i / 34)
        shock = (r1 - 0.5) * 0.036
        o = price
        c = max(1.0, price * (1 + drift + shock))
        hi = max(o, c) * (1 + 0.012 * r2)
        lo = min(o, c) * (1 - 0.012 * (1 - r2))
        vol = 3.2e7 * (0.6 + r2 + (0.8 if abs(shock) > 0.012 else 0.0))
        rows.append({"t": day.strftime("%Y-%m-%d"), "open": round(o, 2),
                     "high": round(hi, 2), "low": round(lo, 2),
                     "close": round(c, 2), "volume": round(vol)})
        price = c
        day += timedelta(days=1 if day.weekday() < 4 else 3)
    return rows


# ---------------------------------------------------------------- indicators

def sma(vals: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(vals)
    acc = 0.0
    for i, v in enumerate(vals):
        acc += v
        if i >= n:
            acc -= vals[i - n]
        if i >= n - 1:
            out[i] = acc / n
    return out


def ema(vals: list[float], n: int) -> list[float]:
    k = 2 / (n + 1)
    out = [vals[0]]
    for v in vals[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(closes: list[float], n: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    gain = loss = 0.0
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        g, l = max(delta, 0.0), max(-delta, 0.0)
        if i <= n:
            gain += g / n
            loss += l / n
            if i == n:
                out[i] = 100 - 100 / (1 + (gain / loss if loss else float("inf")))
        else:
            gain = (gain * (n - 1) + g) / n
            loss = (loss * (n - 1) + l) / n
            out[i] = 100 - 100 / (1 + (gain / loss if loss else float("inf")))
    return out


def macd(closes: list[float]) -> tuple[list[float], list[float], list[float]]:
    line = [a - b for a, b in zip(ema(closes, 12), ema(closes, 26))]
    signal = ema(line, 9)
    hist = [a - b for a, b in zip(line, signal)]
    return line, signal, hist


def atr(rows: list[dict], n: int = 14) -> list[float | None]:
    trs = []
    for i, r in enumerate(rows):
        if i == 0:
            trs.append(r["high"] - r["low"])
        else:
            pc = rows[i - 1]["close"]
            trs.append(max(r["high"] - r["low"], abs(r["high"] - pc), abs(r["low"] - pc)))
    out: list[float | None] = [None] * len(rows)
    if len(trs) >= n:
        cur = sum(trs[:n]) / n
        out[n - 1] = cur
        for i in range(n, len(trs)):
            cur = (cur * (n - 1) + trs[i]) / n
            out[i] = cur
    return out


def bollinger(closes: list[float], n: int = 20, k: float = 2.0):
    mid = sma(closes, n)
    upper: list[float | None] = [None] * len(closes)
    lower: list[float | None] = [None] * len(closes)
    for i in range(n - 1, len(closes)):
        window = closes[i - n + 1: i + 1]
        m = mid[i]
        sd = math.sqrt(sum((x - m) ** 2 for x in window) / n)
        upper[i] = m + k * sd
        lower[i] = m - k * sd
    return mid, upper, lower


def rnd(seq, digits=2):
    return [None if v is None else round(v, digits) for v in seq]


def compute_technicals(rows: list[dict]) -> dict:
    closes = [r["close"] for r in rows]
    boll_mid, boll_up, boll_lo = bollinger(closes)
    macd_line, macd_sig, macd_hist = macd(closes)
    atr_vals = atr(rows)
    return {
        "sma50": rnd(sma(closes, 50)),
        "sma200": rnd(sma(closes, 200)),
        "boll_mid": rnd(boll_mid), "boll_up": rnd(boll_up), "boll_lo": rnd(boll_lo),
        "rsi": rnd(rsi(closes)),
        "macd": rnd(macd_line, 3), "macd_signal": rnd(macd_sig, 3),
        "macd_hist": rnd(macd_hist, 3),
        "atr": rnd(atr_vals),
    }


# ---------------------------------------------------------------- forecast

def band_label(width_pct: float) -> str:
    if width_pct < 5:
        return "NARROW"
    if width_pct < 10:
        return "MODERATE"
    return "WIDE"


def summarize_forecast(fc: dict | None, last_close: float) -> dict | None:
    if not fc or not fc.get("forecast"):
        return None
    closes = [r["close"] for r in fc["forecast"]]
    pred_close = closes[-1]
    pct = (pred_close - last_close) / last_close * 100
    width = (max(closes) - min(closes)) / last_close * 100
    direction = "UP" if pct > 0.25 else ("DOWN" if pct < -0.25 else "FLAT")
    return {
        "path": fc["forecast"],
        "pred_close": round(pred_close, 2),
        "pct_change": round(pct, 2),
        "direction": direction,
        "band_low": round(min(closes), 2), "band_high": round(max(closes), 2),
        "band_width_pct": round(width, 2),
        "band": band_label(width),
        "interval": fc.get("interval", "1d"),
        "pred_len": fc.get("pred_len", len(closes)),
    }


def demo_forecast(rows: list[dict]) -> dict:
    last = rows[-1]
    price = last["close"]
    day = datetime.strptime(last["t"], "%Y-%m-%d")
    path = []
    for i in range(30):
        day += timedelta(days=1 if day.weekday() < 4 else 3)
        price *= 1 + 0.0016 + 0.004 * math.sin(i / 5)
        path.append({"t": day.strftime("%Y-%m-%d"), "open": round(price * 0.998, 2),
                     "high": round(price * 1.006, 2), "low": round(price * 0.993, 2),
                     "close": round(price, 2), "volume": 3.0e7})
    return {"interval": "1d", "pred_len": 30, "forecast": path}


# ---------------------------------------------------------------- EDGAR

def edgar_get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": EDGAR_UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_fundamentals(ticker: str) -> dict | None:
    try:
        log("looking up CIK on SEC EDGAR...")
        tickers = edgar_get("https://www.sec.gov/files/company_tickers.json")
        cik = None
        for entry in tickers.values():
            if entry["ticker"].upper() == ticker.upper():
                cik = int(entry["cik_str"])
                break
        if cik is None:
            log(f"no CIK found for {ticker} (ETF/crypto/foreign?) — skipping fundamentals")
            return None
        log(f"fetching companyfacts for CIK {cik}...")
        facts = edgar_get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")
        gaap = facts.get("facts", {}).get("us-gaap", {})

        def latest(concepts: list[str], form: str):
            best = None
            for tag in concepts:
                for unit_vals in gaap.get(tag, {}).get("units", {}).values():
                    for v in unit_vals:
                        if v.get("form") != form or "end" not in v:
                            continue
                        if best is None or v["end"] > best["end"] or (
                                v["end"] == best["end"] and v.get("fy", 0) > best.get("fy", 0)):
                            best = v
                if best:
                    break
            return best

        def block(form: str) -> dict:
            out = {}
            period = None
            for label, concepts in EDGAR_CONCEPTS.items():
                v = latest(concepts, form)
                if v:
                    out[label] = v["val"]
                    period = period or v["end"]
            return {"period": period, "values": out} if out else {}

        annual = block("10-K")
        quarterly = block("10-Q")
        if not annual and not quarterly:
            return None
        return {"name": facts.get("entityName", ticker), "cik": cik,
                "annual": annual, "quarterly": quarterly, "source": "SEC EDGAR companyfacts"}
    except Exception as e:  # fundamentals are optional; the sheet renders without them
        log(f"EDGAR fetch failed ({e}) — tearsheet will render without fundamentals")
        return None


DEMO_FUNDAMENTALS = {
    "name": "Demo Corp (synthetic)", "cik": 0,
    "annual": {"period": "2025-12-31", "values": {
        "Revenue": 61_200_000_000, "Net income": 14_800_000_000, "Diluted EPS": 5.92,
        "Cash & equivalents": 21_400_000_000, "Total assets": 96_500_000_000,
        "Total liabilities": 41_300_000_000, "Stockholders equity": 55_200_000_000}},
    "quarterly": {"period": "2026-03-31", "values": {
        "Revenue": 17_100_000_000, "Net income": 4_300_000_000, "Diluted EPS": 1.71,
        "Cash & equivalents": 23_100_000_000, "Total assets": 99_800_000_000,
        "Total liabilities": 42_000_000_000, "Stockholders equity": 57_800_000_000}},
    "source": "synthetic demo data",
}


# ---------------------------------------------------------------- news

def fetch_news(ticker: str, limit: int = 5) -> list[dict]:
    try:
        import yfinance as yf

        items = []
        for n in (yf.Ticker(ticker).news or [])[:limit]:
            content = n.get("content", n)
            title = content.get("title")
            if not title:
                continue
            items.append({
                "title": title,
                "publisher": (content.get("provider") or {}).get("displayName")
                if isinstance(content.get("provider"), dict)
                else n.get("publisher", ""),
                "date": (content.get("pubDate") or "")[:10],
                "url": (content.get("canonicalUrl") or {}).get("url")
                if isinstance(content.get("canonicalUrl"), dict) else n.get("link", ""),
            })
        return items
    except Exception as e:
        log(f"news fetch failed ({e}) — tearsheet will render without news")
        return []


DEMO_NEWS = [
    {"title": "Demo Corp beats on revenue, raises full-year guidance", "publisher": "Sample Wire",
     "date": "2026-07-18", "url": ""},
    {"title": "Analysts split on Demo Corp valuation after 40% run", "publisher": "Sample Journal",
     "date": "2026-07-14", "url": ""},
    {"title": "Demo Corp announces $5B buyback program", "publisher": "Sample Wire",
     "date": "2026-07-02", "url": ""},
    {"title": "Sector rotation puts pressure on high-multiple names", "publisher": "Sample Times",
     "date": "2026-06-27", "url": ""},
]


# ---------------------------------------------------------------- house call

def house_call(rows: list[dict], tech: dict, forecast: dict | None) -> dict:
    last = rows[-1]["close"]
    score = 0
    reasons = []

    s200 = tech["sma200"][-1]
    s50 = tech["sma50"][-1]
    if s200 is not None:
        if last > s200:
            score += 1
            reasons.append(f"Price is above the 200-day SMA (${s200:,.2f}) — long-term uptrend intact.")
        else:
            score -= 1
            reasons.append(f"Price is below the 200-day SMA (${s200:,.2f}) — long-term trend is against you.")
    if s50 is not None and s200 is not None:
        if s50 > s200:
            score += 1
            reasons.append("50-day SMA is above the 200-day (golden-cross regime).")
        else:
            score -= 1
            reasons.append("50-day SMA is below the 200-day (death-cross regime).")

    r = tech["rsi"][-1]
    if r is not None:
        if r > 70:
            score -= 1
            reasons.append(f"RSI at {r:.0f} is overbought — chasing here is paying up.")
        elif r < 30:
            score += 1
            reasons.append(f"RSI at {r:.0f} is oversold — selling pressure may be exhausted.")
        else:
            reasons.append(f"RSI at {r:.0f} is neutral.")

    h = tech["macd_hist"][-1]
    if h is not None:
        if h > 0:
            score += 1
            reasons.append("MACD histogram is positive — short-term momentum favors buyers.")
        else:
            score -= 1
            reasons.append("MACD histogram is negative — short-term momentum favors sellers.")

    if forecast:
        d, band = forecast["direction"], forecast["band"]
        if band == "WIDE":
            reasons.append(f"Kronos band is WIDE (±{forecast['band_width_pct']:.1f}%) — "
                           "the forecast is noise; it gets zero weight in this call.")
        elif d == "UP":
            score += 2 if band == "NARROW" else 1
            reasons.append(f"Kronos forecasts {forecast['pct_change']:+.1f}% with a {band} band — "
                           "treated as a supporting signal.")
        elif d == "DOWN":
            score -= 2 if band == "NARROW" else 1
            reasons.append(f"Kronos forecasts {forecast['pct_change']:+.1f}% with a {band} band — "
                           "treated as a warning signal.")
        else:
            reasons.append("Kronos forecast is FLAT — no directional weight.")
    else:
        reasons.append("No Kronos forecast supplied — call is technicals-only. "
                       "Run the skill with KRONOS_JSON_OUT for the full picture.")

    call = "BUY" if score >= 3 else ("SELL" if score <= -2 else "HOLD")
    return {"call": call, "score": score, "reasons": reasons,
            "method": "Transparent rule score: trend (SMA 50/200) + momentum (RSI, MACD) "
                      "+ Kronos direction weighted by band width. Disagree with it — that is the point."}


# ---------------------------------------------------------------- assembly

def build(args: argparse.Namespace) -> Path:
    ticker = args.ticker.upper()
    if args.demo:
        rows = demo_ohlcv()
        fc_raw = demo_forecast(rows)
        fundamentals = DEMO_FUNDAMENTALS
        news = DEMO_NEWS
    else:
        rows = fetch_ohlcv(ticker, args.period, args.interval)
        fc_raw = json.loads(Path(args.forecast).read_text()) if args.forecast else None
        fundamentals = fetch_fundamentals(ticker)
        news = fetch_news(ticker)

    tech = compute_technicals(rows)
    forecast = summarize_forecast(fc_raw, rows[-1]["close"])
    call = house_call(rows, tech, forecast)

    data = {
        "ticker": ticker,
        "demo": bool(args.demo),
        "generated": datetime.now().strftime("%A, %B %d, %Y"),
        "period": args.period, "interval": args.interval,
        "ohlcv": rows,
        "technicals": tech,
        "forecast": forecast,
        "fundamentals": fundamentals,
        "news": news,
        "house_call": call,
    }

    html = TEMPLATE.read_text()
    if DATA_PLACEHOLDER not in html:
        raise SystemExit(f"template.html is missing the {DATA_PLACEHOLDER} placeholder")
    # "</" must not appear literally inside the inline <script> JSON block
    html = html.replace(DATA_PLACEHOLDER, json.dumps(data).replace("</", "<\\/"))

    OUTPUT_DIR.mkdir(exist_ok=True)
    out = Path(args.out) if args.out else OUTPUT_DIR / f"{ticker}.html"
    out.write_text(html)
    log(f"wrote {out}")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Generate a Kronos Ledger tearsheet")
    p.add_argument("ticker")
    p.add_argument("--period", default="1y")
    p.add_argument("--interval", default="1d")
    p.add_argument("--forecast", help="path to KRONOS_JSON_OUT file from the skill")
    p.add_argument("--demo", action="store_true", help="offline synthetic data")
    p.add_argument("--out", help="output HTML path (default tearsheet/output/<TICKER>.html)")
    build(p.parse_args())
    return 0


if __name__ == "__main__":
    sys.exit(main())
