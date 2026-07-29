# Simply Wall St Investment Research Agent — Methodology

> **Data source policy:** All company analysis in this repository is sourced exclusively from
> [Simply Wall St](https://simplywall.st) (fair value estimates, snowflake scores, growth
> forecasts, financial health checks, and risk/warning flags). No opinions from other websites
> are used unless explicitly requested.

## Objective

Identify companies that are **genuinely undervalued with excellent long-term prospects** —
businesses that can outperform over the next 5–10 years — not merely companies with low
valuation multiples.

## Screening requirements

A candidate should meet as many of these as possible:

| # | Criterion |
|---|-----------|
| 1 | Trading below Simply Wall St Fair Value estimate |
| 2 | Margin of Safety > 20% |
| 3 | Forward P/E below industry average |
| 4 | PEG ratio < 1.5 (where available) |
| 5 | Strong expected earnings growth |
| 6 | Strong expected revenue growth |
| 7 | Healthy balance sheet |
| 8 | Positive and growing free cash flow |
| 9 | High return on equity |
| 10 | High return on invested capital |
| 11 | Strong future growth score |
| 12 | Strong financial health score |
| 13 | Good management score |
| 14 | No major warning flags unless clearly explainable |

**Automatic rejections:** companies that are cheap purely because of declining earnings,
excessive debt, poor cash generation, shrinking industries, or major structural problems.

## Quality checks (asked before any recommendation)

1. Why is the market undervaluing it?
2. Is the business improving?
3. Is earnings growth sustainable?
4. Does it have a durable competitive advantage?
5. Is management allocating capital effectively?
6. Could this business realistically be much larger in 5–10 years?

If the answers are weak, the company is rejected regardless of valuation.

## Scoring system (out of 100)

| Component | Weight |
|---|---|
| Valuation | 30 |
| Future Growth | 25 |
| Financial Health | 20 |
| Management Quality | 10 |
| Past Performance | 10 |
| Overall Risk | 5 |

- **Minimum score to recommend: 85/100**
- **≥ 90/100 = High Conviction**

## Ranking categories

Each qualifying company is ranked across:

1. Best Opportunity Today
2. Best Long-Term Compounder
3. Highest Margin of Safety
4. Fastest Expected Growth
5. Lowest Risk
6. Most Undervalued Relative to Future Growth

## Output format per recommendation

Company · Ticker · Current Price · SWS Fair Value · Discount to Fair Value (%) ·
Forward P/E · PEG Ratio · Expected Revenue Growth · Expected Earnings Growth ·
Financial Health Summary · Future Growth Summary · Management Summary · Warning Flags ·
Investment Thesis (300–500 words) · Reasons the Market May Be Wrong · Major Risks ·
Bull Case · Bear Case · Buy Rating (1–10) · Confidence Rating · Suggested Entry Range ·
Suggested Hold Time · Overall Score

## Daily behaviour

Whenever new Simply Wall St information becomes available:

1. Re-evaluate every tracked company in `research/reports/`.
2. Update scores in `research/WATCHLIST.md`.
3. Identify new opportunities from the latest SWS undervalued/growth screens.
4. Remove companies whose investment case has weakened (log the removal and reason).
5. Highlight companies whose valuation has become significantly more attractive.
6. Maintain the ranked watchlist of the top 25 highest-conviction opportunities.

## Repository layout

```
research/
  METHODOLOGY.md          ← this file
  WATCHLIST.md            ← ranked top-25 conviction watchlist (living document)
  reports/
    YYYY-MM-DD-report.md  ← dated full research reports
  rejected/
    REJECTED.md           ← rejection log with reasons (prevents re-work)
```

## Data limitations (disclosure)

- Simply Wall St company profile pages are bot-protected; data is collected from
  Simply Wall St's published news/analysis articles, which carry the same fair value,
  growth-forecast, health, and risk-flag data. Figures are as of each article's date.
- Some fields (exact snowflake scores, ROIC, industry-average forward P/E) are not always
  published in article form; these are marked "n/a (not published)" rather than estimated.
- Nothing here is financial advice. This is an automated research log for personal use.
