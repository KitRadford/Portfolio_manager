# The Routine

The stack only matters if you actually run it on a schedule. This is the routine that turns
the tools into a research system — and the guardrails that keep it from turning into a
gambling habit.

## Weekly

### 1. Pick (and keep) a watchlist of 5–10 tickers

Any more and you cannot keep up with the quarterly refresh. Start narrow. The list lives in
[`watchlist.md`](../watchlist.md).

### 2. Run the Kronos skill on each ticker

Ask Claude in plain English ("run kronos on AAPL") or:

```bash
python3 .claude/skills/kronos/scripts/run_kronos.py <TICKER> 1y 1d 30
```

Log the direction and the confidence band in the watchlist table. **Flag only the names with
a narrow band in the same direction across at least two timeframes** (e.g. daily and weekly).

### 3. Generate a Ledger for any flagged ticker

```bash
KRONOS_JSON_OUT=forecast.json \
    python3 .claude/skills/kronos/scripts/run_kronos.py <TICKER> 1y 1d 30
python3 tearsheet/generate_tearsheet.py <TICKER> --forecast forecast.json
```

One page, one ticker, one house call you can disagree with.

### 4. Open the Claude Project for the same ticker

Re-read the bull-case and bear-case memos in [`memos/`](../memos). Ask Claude what would
invalidate the current bear case — that answer is your exit thesis.

## Quarterly (when the 10-Q drops)

1. Add the new 10-Q (and any new transcripts/decks) to the ticker's Claude Project.
2. Ask: did management deliver what the bull case assumed? Did the numbers improve? Did
   anything in the bear case get worse?
3. Update both memos. Re-generate the Ledger.

## Setting up a ticker's Claude Project (the fundamental side)

Create one Claude Project per ticker. In the Project instructions, lock in the grounding
rule — **in the instructions, not the chat**, or the memos will quietly hallucinate:

> Only use the documents in this Project's knowledge base. Do not use outside knowledge.
> Do not speculate. If information is missing, say so explicitly.

Then load it: last 5 years of annual reports, the most recent quarterly earnings, every
earnings call transcript, current investor decks — all from the company's investor relations
page. Ask for two short memos: a bull case for owning the stock, and a bear case for losing
money on it. Save both to `memos/<TICKER>-bull.md` and `memos/<TICKER>-bear.md`.

## The guardrails

- **The interval rule.** Narrow band across at least two timeframes = look. Wide band =
  ignore. A single prediction on a single timeframe is not a signal.
- **The filter-vs-amplifier test.** If the stack is filtering you *out* of tickers that did
  not deserve attention, it is working. If you find yourself overriding the stack because a
  stock is running, it is no longer working. Reset.
- **The Ledger frame.** The tearsheet does not replace your decision-making; it makes the
  research legible. Print it before earnings if you want to be honest with yourself about
  why you owned it.
- Not financial advice. Stocks carry real risk.
