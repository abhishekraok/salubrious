# Decision quality analysis

The **Decisions** page is a local, retrospective comparison of buy-like allocation
actions with VFFVX. It is intended to make past choices inspectable, not to label
the person or the decision process as good or bad.

## Private data flow

Run the importer from the repository root:

```bash
server/.venv/bin/python server/scripts/import_finance_history.py /path/to/raw-pdfs
```

The importer reads PDFs in place. It does not copy the PDFs or persist extracted
statement text. It writes only normalized artifacts to `.private/finance/`:

- `transactions.csv`: dated, normalized ledger rows with pseudonymous account keys
- `performance_periods.csv`: statement/performance summaries that are not transaction ledgers
- `sources.json`: source hashes, parser provenance, coverage, and market-data status
- `market_data/*.csv`: cached daily price history used for repeatable scoring
- `action_quality.json`: the API-ready visualization payload
- `parse_warnings.csv`: structured warnings without raw statement text
- `assets_sheet_*.csv` and `assets_sheet_source.json`: the read-only Assets workbook reference

The repository `.gitignore` excludes the entire `.private/` directory. The importer
also sets `.private/` and `.private/finance/` to owner-only permissions when the
filesystem supports it.

## Standardization and source precedence

Transaction rows use ISO dates, exact decimal strings, normalized action names,
stable hashes, source provenance, and separate source/normalized signs. `cash_effect`
uses the account-cash perspective: purchases, reinvestments, and sweep-ins are
negative; sales, distributions, and sweep-outs are positive; non-cash exchanges
and external transfers are blank. Names, addresses, employer names, and account
numbers are not persisted.

PDF transaction ledgers are primary evidence. Fidelity annual statements and Schwab
performance reports become period summaries rather than invented transaction rows.
The Google Sheets **Assets** workbook is secondary evidence because it combines
snapshots, plans, and free-text action notes; discrepancies are retained, and sheet
notes never overwrite or fabricate ledger activity.

## Regret-style measure

The primary result includes only mature actions with a full 365-day observation:

```text
action advantage = purchased-security adjusted-close return - VFFVX adjusted-close return
opportunity cost = max(0, -action advantage × action notional)
```

Entry uses the first common trading date on or after the action date. Evaluation
uses the last common trading date on or before the 365-day horizon. A ±2 percentage
point band is labeled **similar**; values outside it are **ahead** or **behind**.

Recurring plan contributions are treated as executions of a standing allocation
policy rather than independent discretionary decisions. Dividends, reinvestments,
sweeps, conversions, unmatched sells, missing tickers, and proprietary plan funds
are also not scored. Adjusted-close returns already include fund distributions, so
excluding dividend/reinvestment rows avoids double counting.

Per-action counterfactuals overlap. Their opportunity costs are descriptive and must
not be added or interpreted as a causal portfolio loss. VFFVX is also an age-specific
glide-path fund, so it is not a fair alternative for every bond, cash, tax, liquidity,
or plan-constrained decision.
