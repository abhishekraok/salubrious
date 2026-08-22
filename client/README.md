# Salubrious Client

React and TypeScript frontend for Salubrious, built with Vite and Tailwind CSS.

## Requirements

- Node.js `^20.19.0` or `>=22.12.0`
- The Salubrious API running at `http://localhost:8000` for live data

The development server proxies `/api` requests to the backend.

## Commands

Install the locked dependencies:

```bash
npm ci
```

Start the development server:

```bash
npm run dev
```

Run the same frontend verification used in CI:

```bash
npm run lint
npm run build
```

Preview the production build locally:

```bash
npm run preview
```

The current routed interface contains Today, Plan, Holdings, Allocation, and Spending. Category-level insights appear on Today; Review, journal, and behavioral override workflows are deferred.
