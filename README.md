# Salubrious

A calm portfolio tracking app. Designed to surface only what matters, reduce impulsive decisions, and help you stick to your investment plan.

This is not a trading app. There are no daily P/L charts, no red/green flashing numbers, and no gamification. Instead, it tells you when your portfolio has drifted enough to act.

## Philosophy

- **Fewer, better decisions.** The app shows a single headline on the Today page: either "No action needed" or a specific, actionable recommendation.
- **Drift-based rebalancing.** Tolerance bands (based on Daryanani 2008) determine when to act, not calendar dates or gut feelings.
- **Calm by default.** The primary experience avoids short-term performance noise and emphasizes policy status and spending security.
- **Two targeting modes.** Track your portfolio by exact fund weights (fund mode) or by high-level category targets like equity %, international %, value tilt %, and small cap % (category mode). Category mode lets you swap funds without changing your targets.

## Quick Start

**Requirements:** Python 3.11+ and Node.js `^20.19.0` or `>=22.12.0` (CI uses Node.js 22)

```bash
# Backend
cd server
python3 -m pip install -e .
cd ..

# Frontend
cd client
npm ci
cd ..

# Seed example data (Bernstein 3-fund portfolio)
make seed

# Run (in two terminals)
make server   # http://localhost:8000
make client   # http://localhost:5173
```

Open http://localhost:5173. Prices auto-refresh on first load.

## Pages

| Page | Purpose |
|------|---------|
| **Today** | Single headline recommendation: calm, watch, or action needed |
| **Plan** | Investment policy, targeting mode toggle, fund/category targets |
| **Holdings** | Account and holding management, CSV import/export |
| **Allocation** | Per-fund drift and band status (fund mode only) |
| **Decisions** | Private, benchmark-relative review of historical allocation actions |
| **Spending** | Safe asset runway, cash reserve, funded status, what-if scenarios, and simulation |

Category-level portfolio insights are shown on the Today page. Review scheduling, a decision journal, and behavioral override guardrails are deferred and are not part of the current routed interface.

## Targeting Modes

**Fund mode** — set a target percentage for each fund. The Allocation page shows per-fund drift with tolerance bands.

**Category mode** — set four high-level targets:
- Equity % (of total portfolio)
- International % (of equities)
- Value-tilted % (of equities)
- Small cap % (of equities)

The Today page shows gauge rings with OK/Watch/Action status for each. Swap VXUS for IXUS and your targets don't change.

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy 2.0, SQLite
- **Frontend:** React, TypeScript, Tailwind CSS, Vite
- **Prices:** Yahoo Finance via yfinance (free, auto-refreshes hourly)
- **No auth** — single-user, runs locally

## Data

All data lives in `server/salubrious.db` (SQLite, gitignored). To start fresh:

```bash
make db-reset
```

Holdings can be exported/imported via CSV on the Holdings page.

Historical transaction and decision-quality imports live only under the gitignored
`.private/` directory. See [Decision quality analysis](docs/decision-quality.md) for
the normalized formats, importer command, source precedence, and methodology.

## Development

Run the app from the repository root:

```bash
make server    # Start backend with hot reload
make client    # Start frontend with hot reload
make seed      # Seed database with example data
make db-reset  # Delete database and reseed
```

Verify backend changes:

```bash
cd server
python3 -m pip install -e ".[dev]"
pytest tests/ -v
```

Verify frontend changes:

```bash
cd client
npm ci
npm run lint
npm run build
```

The GitHub Actions workflow runs the backend test suite and the frontend install, lint, and production build checks on pushes and pull requests to `main`.

## License

Apache 2.0 — see [LICENSE](LICENSE)
