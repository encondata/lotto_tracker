# Lone Star — Lotto Ledger

A multi-user web app for tracking lottery play, tickets, and prizes across five Texas
games: **Powerball, Mega Millions, Lotto Texas, Texas Two Step, and Daily 4**.

Enter tickets by hand or by photographing them (OCR pre-fills a confirm form). A daily
pipeline pulls the official Texas Lottery winning numbers, matches them against your
tickets, and auto-calculates winnings. A polished, animated dashboard shows spend,
winnings, net, ROI, and more.

- **Backend:** FastAPI + SQLAlchemy 2.0 + PostgreSQL (143 tests)
- **Frontend:** React + TypeScript (Vite), GSAP, three.js (react-three-fiber)
- **Theme:** "Lone Star Draw Room" — a late-night lottery studio

## Prerequisites

- Docker Desktop (for PostgreSQL + the backend container)
- Python 3.12+ and Node 20+ (for local dev / the frontend)

## Quick start

```bash
# 1. Start Postgres + the backend API (published on http://localhost:8000)
docker compose up -d --build

# 2. Apply migrations + seed games, prize rules, and demo data
cd backend
python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
export DATABASE_URL=postgresql+psycopg://lotto:lotto@localhost:5433/lotto
alembic upgrade head
python -m app.seed        # 5 games + prize rules
python -m app.demo        # demo users + demo tickets + matched results

# 3. Run the frontend (http://localhost:5173, proxies /api → :8000)
cd ../frontend
npm install
npm run dev -- --host      # --host makes it reachable from your phone on the LAN
```

> **Note:** Postgres is published on host port **5433** (5432 is often already in use).
> Inside Docker the backend still reaches it at `db:5432`.

## Demo accounts

| Role  | Email                   | Password     |
|-------|-------------------------|--------------|
| User  | `demo@lottotracker.io`  | `demo12345`  |
| Admin | `admin@lottotracker.io` | `admin12345` |

The demo user comes preloaded with tickets across all five games — wins, losses, and a
pending ("money in play") ticket — so the dashboard and analytics are populated.

## How winnings are computed

- Winning numbers come from the official Texas Lottery CSV feeds (`app/results/csv_ingest.py`).
- The **prize engine** (`app/prizes/`) computes exact winnings from game rules for the
  fixed-prize games (Powerball, Mega Millions, Daily 4).
- **Lotto Texas** and **Texas Two Step** have pari-mutuel tiers whose payouts vary per
  draw; those amounts come from per-draw payout data stored on each `draw`. An admin can
  also record draws (and payouts) manually as a fallback.

## Testing

```bash
cd backend && . .venv/bin/activate && pytest -q      # requires `docker compose up -d db`
cd frontend && npm run build                          # type-check + production build
```

## Configuration

Backend settings (env vars, see `backend/app/config.py`):

- `DATABASE_URL` — Postgres connection string.
- `CORS_ALLOW_ORIGINS` — comma-separated origins; `*` (default) for LAN dev.
- `JWT_SECRET` — set a strong value in production (the dev default is insecure).
- `OCR_PROVIDER` — `mock` (default). A real cloud vision provider can be added behind the
  `OcrProvider` interface in `app/ocr/` (see `app/ocr/__init__.py`).

## Design & specs

- Design spec: [`docs/superpowers/specs/2026-07-02-lottery-tracker-design.md`](docs/superpowers/specs/2026-07-02-lottery-tracker-design.md)
- Foundation plan: [`docs/superpowers/plans/2026-07-02-foundation.md`](docs/superpowers/plans/2026-07-02-foundation.md)

## Deferred (not in this build)

- Email/push notifications (the UI surfaces a "new results" state instead).
- Live pari-mutuel payout scraping (interface exists; admin manual entry covers it).
- A real OCR vision provider (mock provider ships so the scan→confirm flow works).
