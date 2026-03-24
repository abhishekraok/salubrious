# Salubrious Specification

## 1. Purpose

Build a **personal finance / portfolio tracking app** optimized for the user’s **long-term well-being**, not engagement.

This app is explicitly the opposite of a brokerage UX that encourages frequent checking, trading, anxiety, and noise consumption.

The app’s job is to:

1. Help the user define a long-term investment policy.
2. Monitor portfolio state relative to that policy.
3. Surface only **actionable** information.
4. Reduce impulsive decision-making.
5. Support long-term expected consumption utility, stable spending, and psychological calm.

The app should feel like a **calm portfolio operating system**, not a trading terminal.

---

## 2. Product Philosophy

### Core principle

The app optimizes for **better decisions and fewer decisions**.

### Anti-goals

The app should **not**:

- maximize app engagement
- encourage discretionary trading
- emphasize daily or intraday gains/losses
- present market news as a primary UI feature
- gamify investing
- use bright reward/punishment visuals around short-term returns

### Design principles

1. **Actionable over interesting**\
   Show only information that can lead to a rational action.
2. **Policy over prediction**\
   Default to rules and plans, not market commentary.
3. **State before action**\
   First show whether the user is on plan; only then show any suggested action.
4. **Calm by default**\
   The most common output should be: **No action needed.**
5. **Spending security over wealth excitement**\
   Emphasize spending runway and life stability over point-in-time wealth fluctuations.
6. **Friction for harmful overrides**\
   Make it slightly harder to deviate from plan impulsively.
7. **Minimal cognitive load**\
   The main page should be understandable in under 10 seconds.

---

## 3. Primary User

Initial version is for a **single user (self-use)**.

Assumptions:

- user has a target asset allocation
- user values long-term discipline
- user may hold multiple accounts across brokerages
- user prefers infrequent action
- user cares about taxes, rebalancing, and behavioral discipline
- user wants software that protects them from over-monitoring and overreacting

This spec should support later generalization to other users, but initial product decisions may be optimized for one sophisticated investor.

---

## 4. Product Jobs To Be Done

The app must do these jobs well:

1. **Let me define my target portfolio and implementation rules.**
2. **Tell me whether I need to do anything right now.**
3. **Tell me what exact action is recommended, if any.**
4. **Help me rebalance with minimal unnecessary trading and tax cost.**
5. **Show me whether my spending runway / safe assets are healthy.**
6. **Protect me from checking noise and reacting emotionally.**
7. **Create a durable written policy that I can follow in crashes and bubbles.**

---

## 5. MVP Scope

### In scope for MVP

- manual portfolio entry and/or CSV import
- target allocation setup
- tolerance bands
- current vs target allocation view
- top-level recommended action engine
- cash-flow-aware rebalance suggestions
- safe assets / spending runway display
- review schedule tracking
- basic decision journal
- behavioral guardrails in UI

### Nice-to-have after MVP

- broker API sync
- tax lot awareness
- tax-loss harvesting suggestions
- multiple accounts with tax-aware rebalance routing
- crash plan automation
- notification engine
- calendar-based review reminders
- scenario analysis

### Explicitly out of scope for MVP

- live trading execution
- options, leverage, margin, crypto speculation workflows
- social feed, market news, pundit content
- chatty AI market commentary
- advanced performance benchmarking

---

## 6. Information Architecture

Use a simple left nav or tab bar with these sections:

1. **Today**
2. **Plan**
3. **Allocation**
4. **Spending**
5. **Review**
6. **Settings**

Optional later:
7\. **Taxes**
8\. **Accounts**
9\. **Journal**

---

## 7. UX / Visual Design Requirements

### Tone

- calm
- sober
- analytical
- non-gamified
- low-stimulation

### Visual style

- neutral palette (grays, off-white, muted blue/green)
- restrained accent colors
- minimal motion/animation
- large whitespace
- readable typography
- no flashing numbers
- no confetti, badges, celebratory P/L visuals

### Color semantics

- neutral / gray: no action needed
- muted green: on plan / healthy
- amber: watch / soft deviation
- red: real action required

### UX rules

- Do **not** show daily gains/losses on the home page.
- Do **not** show intraday charts anywhere by default.
- Do **not** auto-refresh prices in a way that encourages compulsive checking.
- Performance views should be hidden behind an explicit click.
- Default performance intervals should be monthly, yearly, and since inception; not daily.

---

## 8. Page Specifications

# 8.1 Today Page

## Goal

Answer one question: **What, if anything, should I do now?**

## Layout

### Top status card (most important element)

Display exactly one primary recommendation:

- No action needed
- Rebalance with new contributions only
- Rebalance required
- Review target allocation
- Spending runway below target
- Crash plan trigger active
- Annual review due

Below the main line, show a short explanation.

Example:

- **No action needed**\
  All allocation sleeves are within tolerance bands. Next scheduled review: July 1, 2026.

Or:

- **Rebalance required**\
  VGIT is 2.3 percentage points below target and SGOV is 2.6 points above target. Suggested action available.

### Summary cards

Show 4–6 compact summary blocks:

- Portfolio status: On plan / Watch / Action needed
- Spending runway: e.g. 4.2 years safe spending funded
- Safe asset level: e.g. \$460,000 vs target \$400,000
- Review schedule: next review date
- Last action taken
- Decision journal status (optional)

### Secondary section: active issues

Only show items requiring attention:

- assets outside hard band
- review overdue
- crash trigger reached
- spending floor not sufficiently funded

If nothing is wrong, show a calming state:

- “Everything is within policy. You do not need to act.”

## Non-requirements

Do not show:

- daily P/L
- top movers
- news
- sparkline charts
- financial headlines

---

# 8.2 Plan Page

## Goal

Store the user’s explicit investment policy.

## Sections

### A. Objective

Fields:

- policy name
- objective statement
- notes

Default objective text:

> Maximize long-term expected consumption utility while minimizing unnecessary cognitive load and behavioral mistakes.

### B. Target portfolio

Editable list of sleeves with:

- asset label
- ticker symbol
- target percentage
- asset class
- geography
- account preference (optional)
- notes

Example:

- VTI — 10%
- AVLV - 10%
- VXUS — 20%
- AVUV — 10%
- AVDV — 10%
- VGIT — 20%
- VTIP — 10%
- SGOV — 10%

Require sum = 100%.

### C. Rebalancing policy

Fields:

- review cadence: annual / semiannual / quarterly / custom
- rebalance method: threshold / calendar / hybrid
- use cash flows first: yes/no
- allow taxable sales: yes/no
- hard rebalance allowed only at review date: yes/no

Defaults:

- cadence = annual
- method = hybrid
- use cash flows first = yes
- taxable sales = avoid if possible

### D. Tolerance bands

For each sleeve or globally, define:

- soft band
- hard band

Recommended default formula:

- soft band = max(1.0 percentage point, 10% of target weight)
- hard band = max(1.5 percentage points, 20% of target weight)
- optionally cap at 5 percentage points

Allow override per sleeve.

### E. Spending policy

Fields:

- baseline annual spending
- comfortable annual spending
- emergency annual spending
- target safe asset runway in years
- minimum cash-like reserve

### F. Crash plan

Optional structured drawdown plan.
Each trigger includes:

- trigger condition (e.g. total equity drawdown from high)
- source asset to sell
- target asset(s) to buy
- amount or % to deploy
- notes

### G. Things I do not do

Freeform precommitment list, e.g.:

- I do not react to headlines.
- I do not sell equities because of fear.
- I do not change asset allocation without a life change or scheduled review.

This section is psychologically important and should feel like a personal constitution.

---

# 8.3 Allocation Page

## Goal

Show current portfolio state relative to target, clearly and actionably.

## Primary table

Columns:

- Asset / Ticker
- Current Value
- Current %
- Target %
- Drift (pp)
- Soft Band
- Hard Band
- Status

Status values:

- OK
- Watch
- Action needed

### Row behavior

- inside soft band → neutral
- outside soft but inside hard → amber
- outside hard → red

### Summary above table

Show:

- total portfolio value
- number of sleeves outside soft band
- number of sleeves outside hard band
- whether rebalance is needed

## Allocation chart

Optional donut or stacked bar.
Keep it simple and muted.
This is secondary to the table, not primary.

## Suggested action panel

This should compute the minimum-action recommendation.

Examples:

- Direct next \$8,000 contribution to VGIT
- Exchange \$12,000 from SGOV to VXUS
- No action until next review

The suggestion engine should prefer, in order:

1. new cash flows
2. tax-advantaged account changes
3. cash-like assets as funding source
4. taxable sales only as last resort

### Explainability requirement

Every recommendation must have a short “why” explanation.

Example:

> SGOV is 2.4 points above target and VGIT is 2.1 points below target. A transfer from SGOV to VGIT restores fixed-income allocation without taxable equity sales.

---

# 8.4 Spending Page

## Goal

Connect the portfolio to actual life support and spending stability.

## Core metrics

Show:

- baseline annual spending
- comfortable annual spending
- current annual spending estimate
- safe asset amount
- safe asset years of runway
- current portfolio withdrawal rate (simple estimate)
- funded status: secure / watch / constrained

## Derived metrics

Examples:

- “Safe assets cover 4.1 years of baseline spending.”
- “A 10% equity decline would not affect baseline spending this year.”
- “You are above your minimum reserve target by \$60,000.”

## Scenario widgets

Lightweight, not over-engineered.
Allow user to see:

- if spending increases by \$10k/year
- if safe asset target rises from 3 years to 5 years
- if portfolio drops by 20%

Outputs should be framed in spending terms, not just wealth terms.

---

# 8.5 Review Page

## Goal

Support intentional, infrequent, high-quality reviews.

## Sections

### Review schedule

Show:

- next review date
- last completed review date
- overdue status

### Review checklist

Checklist items:

- Did my life goals change?
- Did my spending needs change?
- Did my risk capacity change?
- Did my job / human capital risk change?
- Did my target portfolio change for a durable reason?
- Is tax strategy still appropriate?
- Is safe asset runway still sufficient?

### Historical review log

Each review entry contains:

- date
- summary
- what changed
- rationale
- whether allocation changed

### Decision journal

Log any major manual override or discretionary change.
Fields:

- date
- action taken
- reason category
- freeform explanation
- confidence level
- follow-up review date

Reason categories:

- goal change
- spending change
- tax change
- liquidity need
- anxiety/fear
- reacting to news
- conviction change
- other

---

# 8.6 Settings Page

## Important settings

- hide performance by default
- show values in dollars / percentages / both
- review reminder cadence
- preferred tolerance band defaults
- behavioral friction settings
- import/export data

### Behavioral settings

Allow user to enable:

- 24h cooldown before manual plan override
- hidden performance unless explicitly revealed
- limit portfolio check-ins to once per day/week (soft reminder)
- require journal entry for manual rebalance outside policy

---

## 9. Data Model

Design a simple domain model first.

### Entities

#### UserProfile

- id
- name
- currency
- created\_at
- updated\_at

#### InvestmentPolicy

- id
- user\_id
- name
- objective\_text
- review\_cadence
- rebalance\_method
- use\_cash\_flows\_first
- avoid\_taxable\_sales
- baseline\_annual\_spending
- comfortable\_annual\_spending
- emergency\_annual\_spending
- safe\_asset\_runway\_years\_target
- minimum\_cash\_reserve
- created\_at
- updated\_at

#### PortfolioSleeve

Represents a target slice.

- id
- policy\_id
- ticker
- label
- target\_percent
- asset\_class
- geography
- factor\_tag
- preferred\_account\_type
- soft\_band\_percent\_points
- hard\_band\_percent\_points
- notes

#### Account

- id
- user\_id
- institution\_name
- account\_name
- account\_type (taxable, traditional\_ira, roth\_ira, 401k, hsa, cash, etc.)
- is\_tax\_advantaged
- notes

#### Holding

- id
- account\_id
- ticker
- quantity
- price
- market\_value
- as\_of\_date

#### PortfolioSnapshot

- id
- user\_id
- total\_value
- total\_safe\_assets
- total\_equities
- as\_of\_date

#### Contribution

- id
- account\_id
- amount
- date
- note

#### ReviewEntry

- id
- policy\_id
- review\_date
- summary
- life\_change\_flag
- allocation\_changed\_flag
- notes

#### JournalEntry

- id
- user\_id
- entry\_date
- action\_type
- reason\_category
- explanation
- confidence\_score
- follow\_up\_date

#### CrashPlanTrigger

- id
- policy\_id
- trigger\_name
- trigger\_type
- threshold\_value
- source\_ticker
- destination\_rule
- action\_amount\_type
- action\_amount\_value
- enabled

---

## 10. Portfolio Computation Logic

### 10.1 Current allocation calculation

For each sleeve:

1. map holdings to sleeves (initially by ticker equality)
2. sum market value by sleeve
3. divide by total portfolio market value
4. compare to target
5. compute drift in percentage points

### 10.2 Safe asset calculation

Need a configurable definition of safe assets.
Allow user to tag tickers or sleeves as:

- cash-like
- nominal bonds
- inflation-linked bonds
- risky assets

Compute:

- safe assets total
- cash-like total
- safe runway years = safe assets / baseline annual spending
- cash runway years = cash-like assets / baseline annual spending

### 10.3 Tolerance band logic

For each sleeve:

- if |drift| <= soft\_band → OK
- if soft\_band < |drift| <= hard\_band → Watch
- if |drift| > hard\_band → Action needed

### 10.4 Rebalance decision logic

Global portfolio states:

- On plan: no sleeve outside soft band
- Mild drift: one or more sleeves outside soft band, none outside hard band
- Rebalance candidate: one or more sleeves outside hard band
- Override required: no feasible low-tax rebalance available

### 10.5 Suggested action engine

Inputs:

- current allocation
- target allocation
- account constraints
- cash balance
- upcoming contributions (optional)
- tax preference flags

Algorithm (MVP simplified):

1. Find overweight sleeves outside band.
2. Find underweight sleeves outside band.
3. Check whether pending/new cash can resolve underweights.
4. Else check if cash-like sleeve can fund underweights.
5. Else recommend minimum dollar transfer between sleeves.
6. Avoid taxable sales where possible.
7. Return one concise recommendation with explanation.

The output should be a structured object:

- headline
- action\_items[]
- rationale
- urgency
- estimated post-trade allocation

---

## 11. Behavioral Guardrail Requirements

These are first-class product features, not decoration.

### 11.1 Default calm state

If no action is required, prominently say so.
This should be the most common app outcome.

### 11.2 Hidden performance

Performance is available but not prominent.
User must explicitly navigate to view it.

### 11.3 No short-term return emphasis

Do not compute or highlight daily returns in primary UX.
If performance is shown later, default to:

- YTD
- 1Y
- 5Y
- Since inception

### 11.4 Friction before manual override

If user attempts to manually change target allocation or execute out-of-policy rebalance, show a modal:

Fields:

- What changed?
- Is this because of a life change or because of market movement?
- Would you make the same decision if markets were closed for 30 days?
- Save journal entry? (required)

### 11.5 Cooling-off option

Optional setting:

- delay any manual allocation change for 24h before confirmation

### 11.6 Review-first policy edits

Strongly encourage major target allocation changes only from the Review page.

---

## 12. Functional Requirements

### FR-1 Manual data entry

User can enter holdings manually by account and ticker.

### FR-2 CSV import

User can import holdings via CSV file.

### FR-3 Target allocation management

User can create and edit a target portfolio with percent weights.
System validates total = 100%.

### FR-4 Band management

User can define global or per-sleeve soft/hard bands.

### FR-5 Allocation computation

System computes current allocation vs target allocation.

### FR-6 Top recommendation

System shows one primary recommendation on Today page.

### FR-7 Rebalance recommendation

System suggests a minimum-action rebalance when needed.

### FR-8 Spending runway

System computes safe asset runway from user inputs.

### FR-9 Review logging

User can log review sessions and policy changes.

### FR-10 Decision journal

User can record discretionary changes and rationale.

### FR-11 Settings-based guardrails

User can enable/disable behavioral friction features.

### FR-12 Persistence

All user-entered data persists locally and/or in database.

---

## 13. Non-Functional Requirements

### NFR-1 Fast load time

Today page should load quickly with minimal visual noise.

### NFR-2 Explainable recommendations

Every suggested action must include plain-English rationale.

### NFR-3 Deterministic logic

Recommendation engine should be deterministic for same inputs.
No AI-generated changing advice in core portfolio logic.

### NFR-4 Auditability

Key decisions should be reconstructable from stored snapshots and review logs.

### NFR-5 Privacy

Initial version should be private and local-first where feasible.
Avoid unnecessary third-party dependencies.

### NFR-6 Simplicity

Prefer straightforward rules and transparent logic over “smart” black-box optimization.

---

## 14. Suggested Tech Approach for Initial Build

A coding agent can choose exact stack, but recommended shape:

### Frontend

- React + TypeScript
- Tailwind CSS
- component library optional but keep visuals restrained

### Backend

- simple Node/TypeScript or Python backend
- REST or tRPC

### Database

- SQLite for local-first MVP, or Postgres if easier

### Data import

- CSV upload first
- broker API integration later

### Architecture style

- thin UI
- clear domain logic layer for portfolio calculations
- recommendation engine as deterministic service module

Suggested modules:

- `portfolio-calculator`
- `allocation-engine`
- `rebalance-engine`
- `spending-engine`
- `policy-engine`
- `journal-service`

---

## 15. Suggested API / Service Boundaries

### PortfolioService

Responsibilities:

- ingest holdings
- compute total values
- map holdings to sleeves
- generate current allocation

### PolicyService

Responsibilities:

- load/save investment policy
- validate target allocation
- manage bands

### RecommendationService

Responsibilities:

- determine overall status
- generate top recommendation
- generate action items

### SpendingService

Responsibilities:

- compute runway
- compute funded status
- run simple spending scenarios

### ReviewService

Responsibilities:

- create review entries
- store decision journal entries
- expose review history

---

## 16. Suggested User Stories

### Core

- As a user, I want to define my target portfolio so that the app can measure drift.
- As a user, I want the home page to tell me whether any action is needed.
- As a user, I want to see current vs target allocation so I can understand drift.
- As a user, I want the app to suggest the lowest-friction rebalance.
- As a user, I want to know whether my safe assets cover my desired spending runway.
- As a user, I want to review my policy periodically rather than react daily.

### Behavioral

- As a user, I want the app to avoid showing noisy daily data by default.
- As a user, I want friction when I try to override my plan impulsively.
- As a user, I want to log why I changed course so that future me can judge the decision.

### Future

- As a user, I want the app to know which accounts are tax-advantaged so it can recommend tax-efficient trades.
- As a user, I want crash-plan triggers to remind me what I precommitted to do.

---

## 17. Acceptance Criteria for MVP

The MVP is successful if:

1. User can enter current holdings and target allocation.
2. App computes current vs target allocation correctly.
3. App shows one primary recommendation on the home page.
4. App highlights sleeves outside tolerance bands.
5. App can suggest a simple rebalance action.
6. App computes safe asset runway from spending inputs.
7. App supports a review log and decision journal.
8. App does not show daily gains/losses on primary screens.
9. App feels calm, minimal, and non-brokerage-like.

---

## 18. Proposed Build Order

### Phase 1: Static skeleton

- create navigation
- stub pages
- local sample data
- implement calm UI system

### Phase 2: Core portfolio engine

- holdings import/manual entry
- target allocation setup
- allocation calculator
- band logic
- top recommendation logic

### Phase 3: Spending + review

- spending runway calculations
- review page
- journal page / journal modal

### Phase 4: Recommendation refinement

- cash-flow-aware suggestions
- account-aware routing
- better rationale text

### Phase 5: Quality polish

- settings
- guardrail modals
- import/export
- persistence hardening

---

## 19. Seed Data / Example Defaults

Use this sample structure during development:

### Target portfolio example (Bernstein 3-fund)

- VTI 34
- VXUS 33
- BND 33

### Spending example

- baseline annual spending = 40000
- comfortable annual spending = 50000
- emergency annual spending = 30000
- target safe asset runway = 4 years
- minimum cash reserve = 10000

### Band example defaults

- VTI: soft 4.2, hard 8.5
- VXUS: soft 4.1, hard 8.2
- BND: soft 4.1, hard 8.2

---

## 20. Future Extensions

Not required now, but design should not block them.

Possible future features:

- multi-user support
- multiple named policies / scenarios
- broker sync
- tax lot optimizer
- tax-loss harvesting partner suggestions
- annual IPS export to PDF
- notifications and reminders
- drawdown-triggered crash plan alerts
- household-level planning and spouse accounts
- expected consumption utility simulator
- Monte Carlo / historical regime stress tests

---

## 21. Final Product Requirement Summary

The app should feel like a **quiet, trustworthy advisor that mostly tells the user to do nothing**.

Its central promise is:

> I will monitor your portfolio continuously, translate it into your life plan, and interrupt you only when action is genuinely justified.

That promise should guide all implementation decisions.

