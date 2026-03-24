# Salubrious

A calm portfolio tracking app. Designed to surface only what matters, reduce impulsive decisions, and help you stick to your investment plan.

This is not a trading app. There are no daily P/L charts, no red/green flashing numbers, no gamification. Instead, it tells you when your portfolio has drifted enough to act — and nudges you to document why before you do.

## Philosophy

- **Fewer, better decisions.** The app shows a single headline on the Today page: either "No action needed" or a specific, actionable recommendation.
- **Drift-based rebalancing.** Tolerance bands (based on Daryanani 2008) determine when to act, not calendar dates or gut feelings.
- **Behavioral guardrails.** A decision journal, "things I do not do" list, and friction before overrides help you stay disciplined.
- **Two targeting modes.** Track your portfolio by exact fund weights (fund mode) or by high-level category targets like equity %, international %, value tilt %, and small cap % (category mode). Category mode lets you swap funds without changing your targets.

## Screenshots

<!-- Add screenshots here -->

## Quick Start

**Requirements:** Python 3.11+, Node.js 18+

```bash
# Clone
git clone <repo-url> && cd salubrious

# Backend
cd server
pip install -e .
cd ..

# Frontend
cd client
npm install
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
| **Insights** | Gauge rings showing equity %, international %, value tilt %, small cap % vs targets |
| **Spending** | Safe asset runway, cash reserve, funded status, what-if scenarios |
| **Review** | Annual review checklist, review log, decision journal |
| **Settings** | Behavioral toggles, manual price refresh |

## Targeting Modes

**Fund mode** — set a target percentage for each fund. The Allocation page shows per-fund drift with tolerance bands.

**Category mode** — set four high-level targets:
- Equity % (of total portfolio)
- International % (of equities)
- Value-tilted % (of equities)
- Small cap % (of equities)

The Insights page shows gauge rings with OK/Watch/Action status for each. Swap VXUS for IXUS and your targets don't change.

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

## Development

```bash
make server    # Start backend with hot reload
make client    # Start frontend with hot reload
make seed      # Seed database with example data
make db-reset  # Delete database and reseed
```

## License

Apache 2.0 — see [LICENSE](LICENSE)
