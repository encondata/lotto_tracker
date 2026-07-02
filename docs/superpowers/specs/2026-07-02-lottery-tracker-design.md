# Lottery Tracker — Design Spec

**Date:** 2026-07-02
**Status:** Approved (brainstorming complete) — ready for implementation planning

## 1. Overview

A multi-user web app for tracking lottery play, tickets, and prizes across five Texas
games. Users enter tickets by hand or by photographing them (OCR pre-fills a confirm
form). A scheduled pipeline pulls each night's winning numbers from the official Texas
Lottery data, matches them against pending tickets, and auto-calculates winnings. A
polished, animated dashboard shows spend, winnings, net, and other analytics.

### Games tracked
Powerball, Mega Millions, Lotto Texas, Texas Two Step, Daily 4.

### Key decisions (from brainstorming)
- **Audience:** private, invite-only; dozens of users; proper per-user isolation; single deployment.
- **Results source:** official Texas Lottery CSV feeds (all 5 games, full history, no auth); scrape per-draw `details.html` pages only for pari-mutuel payouts.
- **OCR:** cloud vision model → structured draft → **always** open a pre-filled confirm form (human-in-the-loop). Degrades to manual entry if OCR fails.
- **Money:** auto-calculate both cost and winnings. Stored as integer **cents** everywhere.
- **Stack:** React + TypeScript SPA (Vite, GSAP, react-three-fiber) → FastAPI (Python) → PostgreSQL.
- **Notifications:** deferred to a later phase. v1 surfaces a "new results" state in the UI on login.

## 2. Architecture

Three-tier, containerized (`docker compose up`).

- **Frontend** — Vite + React + TS SPA. GSAP (UI motion), react-three-fiber/three.js (signature draw-reveal + win celebration). REST/JSON API, JWT auth. TanStack Query for server state; typed API client generated from the FastAPI OpenAPI schema.
- **Backend** — FastAPI, modular:
  - `auth` — invite-based registration, login, JWT, password hashing (argon2/bcrypt).
  - `tickets` — CRUD for tickets + play-lines; per-user isolation.
  - `ocr` — image → cloud vision model → validated structured draft (no direct writes).
  - `results` — daily ingestion pipeline (CSV parse → draws; scrape pari-mutuel payouts).
  - `matching` — match play-lines to draws; compute win/amount via prize engine.
  - `prizes` — rules engine (fixed prize tables + Daily 4 play-type math) + pari-mutuel lookup.
  - `analytics` — aggregate summary queries.
- **Scheduler** — APScheduler (in-process) running the `results` → `matching` pipeline per each game's draw schedule; idempotent.
- **Database** — PostgreSQL via SQLAlchemy + Alembic migrations.
- **Image storage** — local media volume keyed by user; schema ready to swap to S3-compatible storage later.
- **CORS (dev):** backend allows all origins (`allow_origins=["*"]`, or reflect any origin) so the app can be tested from a phone and a laptop on the LAN. This is a dev-friendly default; the setting is env-driven so it can be locked to specific origins in production.

## 3. Data model

UUID PKs. Every user-owned row carries `user_id`. All money in integer cents.

- **`users`** — `id`, `email` (unique), `password_hash`, `display_name`, `role` (`user`|`admin`), `created_at`.
- **`invites`** — `id`, `email`, `token`, `invited_by`, `expires_at`, `accepted_at`.
- **`games`** (seeded reference) — `id`, `key`, `display_name`, `main_count`, `main_min`, `main_max`, `has_special_ball`, `special_min`, `special_max`, `base_price_cents`, `prize_type` (`fixed`|`pari_mutuel`|`mixed`), `draw_schedule` (JSON: days + times).
- **`prize_rules`** (seeded reference) — `game_id`, `tier_key`, `match_main`, `match_special` (bool), `play_type` (Daily 4), `base_amount_cents`, `notes`. Includes Daily 4 + Fireball tables and the fixed tiers of pari-mutuel games.
- **`tickets`** — `id`, `user_id`, `game_id`, `purchase_date`, `image_path` (nullable), `entry_method` (`manual`|`ocr`), `ocr_confidence` (nullable), `add_ons` (JSON: `power_play`, `extra`, `fireball`, `megamillions_multiplier`), `num_draws`, `total_cost_cents`, `created_at`.
- **`play_lines`** — `id`, `ticket_id`, `line_index`, `main_numbers` (int[]), `special_number` (nullable), `play_type` (Daily 4), `wager_cents`, `is_quick_pick`.
- **`draws`** — `id`, `game_id`, `draw_date`, `draw_period` (Daily 4: morning/day/evening/night; else null), `winning_main` (int[]), `winning_special`, `multiplier`, `payouts` (JSON per-tier for pari-mutuel; null for fixed), `source` (`csv`|`scrape`|`manual`), `ingested_at`. **Unique** on `(game_id, draw_date, draw_period)`.
- **`ticket_results`** — `id`, `play_line_id`, `draw_id`, `match_main_count`, `match_special` (bool), `tier_key` (nullable), `amount_won_cents`, `status` (`pending`|`won`|`no_win`), `computed_at`.
- **`ingestion_runs`** (audit) — `id`, `game_id`, `status`, `rows_added`, `errors`, `ran_at`.

**Draw matching:** a ticket's `purchase_date` + `num_draws` resolve which `draws` apply (next N drawings for that game on/after the play date). `ticket_results` are created once the applicable draw is ingested; `status='pending'` until then. A ticket's win total = sum of its lines' `amount_won_cents`.

## 4. Results & matching pipeline

Scheduled, idempotent (upserts keyed on the draw unique constraint). Each game ingests independently.

1. **Ingest CSV** — fetch official per-game CSV, parse into normalized `draws`. First run backfills full history; later runs insert only new draws. `source='csv'`.
2. **Enrich pari-mutuel payouts** — for Lotto Texas + Texas Two Step draws only, fetch that draw's `details.html` and parse the per-tier payout table into `draws.payouts`. Isolated + gated behind step 1: if it breaks, number ingestion and win *detection* still work; only exact pari-mutuel amounts degrade.
3. **Match & compute** — for each pending `play_line` whose game/date now has an ingested draw: count main + special matches → `tier_key` via rules → `amount_won_cents` via prize engine (fixed lookup for Powerball/Mega/Daily 4 applying add-ons and Daily 4 play-type math; scraped `payouts` for pari-mutuel tiers). Write `ticket_results`.
4. **Flag results** — mark newly-won tickets for the UI "new results" state. (No email/push in v1.)

**Resilience:** per-game isolation; `ingestion_runs` audit rows; **admin manual-entry fallback** (`source='manual'`) that matching picks up automatically.

**Scheduling:** jackpot games matched after their night draws (Mon/Tue/Wed/Fri/Sat as applicable per game); Daily 4 after each of its 4 daily draw times. Triggers derived from each game's `draw_schedule`.

## 5. OCR & ticket entry

Both paths converge on the **same confirm form** → single validation path.

- **Manual:** pick game → form adapts to game structure → add play-lines, purchase date, num draws → live cost preview from price/prize rules.
- **OCR:**
  1. Upload/snap image → stored to media volume; ticket row not yet created.
  2. `ocr` module sends image to cloud vision model with strict extraction prompt + JSON schema (game, play-lines, numbers, draw dates, add-ons, wager, per-field confidence).
  3. Normalize + validate against game rules; flag invalid/low-confidence fields.
  4. Same confirm form opens pre-filled, flagged fields highlighted.
  5. On confirm: create ticket + play-lines (`entry_method='ocr'`, confidence stored); schedule matching.
- Vision provider behind an `OcrProvider` interface (swappable: Claude vision, Google Vision, …). Default: an LLM vision model (handles messy multi-line layout, returns structured JSON). Best-effort: total OCR failure degrades to a blank manual form, never blocks.

## 6. Analytics

Read-only SQL aggregations over `tickets`/`play_lines`/`ticket_results`, scoped to the logged-in user (admin may see cross-user aggregate). All money in cents, formatted at presentation.

- **Headline (all-time + date-range):** total spent, total won, net profit/loss, tickets purchased, play-lines played, win rate, biggest single win, ROI %.
- **Breakdowns:** by game (spend/won/net); over time (spend vs winnings by week/month; net-over-time line); by Daily 4 play type; quick-pick vs self-pick win rate; pending vs settled ("money in play").
- Plain `GROUP BY` queries (fast at this scale; materialized view only if it ever grows — YAGNI now). Always consistent with the matching engine's computed results.

## 7. Frontend

- **Structure:** React Router pages; TanStack Query; typed API client from OpenAPI; custom design system (Tailwind or vanilla-extract) — intentional, non-templated look.
- **Screens:** Auth (invite/login) → Dashboard (headline stats + "new results" hero) → Add Ticket (scan/manual confirm form) → Tickets (filter by game/status/date; drill into lines + results) → Analytics → Admin (invites, ingestion status, manual entry).
- **Animation budget (deliberate):**
  - **three.js (react-three-fiber) signature moment:** animated draw-reveal / win celebration (tumbling balls settling on matched numbers; 3D particle burst on a win).
  - **GSAP polish:** route transitions, staggered dashboard card reveals, stat count-ups, net-profit chart draw-on, scan→confirm morph.
  - **CSS craft:** cohesive dark premium theme, per-game color accents, micro-interactions, scroll-reveal.
  - Respect `prefers-reduced-motion`.
- **Design direction:** pull in the `frontend-design` skill during implementation to lock an intentional visual identity.
- **Performance:** three.js scene lazy-loads/code-splits only on screens that use it.

## 8. Reference — Texas Lottery facts (from research, 2025–2026)

### Official winning-number CSV feeds (numbers only, no prize amounts)
- Powerball: `https://www.texaslottery.com/export/sites/lottery/Games/Powerball/Winning_Numbers/powerball.csv`
- Lotto Texas: `https://www.texaslottery.com/export/sites/lottery/Games/Lotto_Texas/Winning_Numbers/lottotexas.csv`
- Mega Millions / Texas Two Step / Daily 4: via each game's `Winning_Numbers/download.html` CSV link (full history).
- Per-draw payout detail pages (pari-mutuel): `.../Games/<Game>/Winning_Numbers/details.html_<id>.html` — per-tier prize + TX winner counts. `<id>` is per-draw (must crawl from the game's winning-numbers page; no date query param).

### Prize computability
| Game | Prize type | Exact winnings from numbers + rules alone? |
|---|---|---|
| Daily 4 | FIXED | Yes — fully (incl. Fireball, given wager + play type) |
| Powerball | FIXED non-jackpot | Yes (capture user's Power Play flag; jackpot from feed) |
| Mega Millions | FIXED tiers × built-in multiplier | Yes (capture per-ticket multiplier; jackpot from feed) |
| Texas Two Step | Mostly PARI-MUTUEL | Partial — 1+Bonus ($7) / 0+Bonus ($5) fixed; rest need per-draw detail page |
| Lotto Texas | PARI-MUTUEL | No — match-4/5/jackpot need per-draw detail page (3-of-6 = $3 and Extra! adds are fixed) |

### Game rules (for the prize engine)
- **Powerball:** 5 of 1–69 + PB 1–26. $2/play. Power Play +$1. Draws Mon/Wed/Sat. 9 tiers; non-jackpot fixed (5=$1M, 4+PB=$50k, 4=$100, 3+PB=$100, 3=$7, 2+PB=$7, 1+PB=$4, 0+PB=$4). Power Play multiplies non-jackpot ×2/3/4/5/10; Match-5+PowerPlay capped at flat $2M; 10× only when jackpot ≤ $150M.
- **Mega Millions (new since Apr 8, 2025):** 5 of 1–70 + Mega Ball 1–24. $5/play. No Megaplier — every play has a **built-in** random multiplier 2/3/4/5/10× on non-jackpot prizes (min non-jackpot win $10). Draws Tue/Fri. Base tiers fixed ($5…$1M pre-multiplier) × per-ticket multiplier.
- **Lotto Texas:** 6 of 1–54. $1/play. Extra! +$1. Draws Mon/Wed/Sat 10:12 PM CT. Pari-mutuel: 6=jackpot, 5≈$2,000*, 4≈$50*, 3=$3 fixed. Extra! fixed adds: 5→+$10k, 4→+$100, 3→+$10, 2→$2 (Extra! only). Extra! not on jackpot.
- **Texas Two Step:** 4 of 1–35 + Bonus 1–35. $1/play. Draws Mon/Thu 10:12 PM CT. Tiers: 4+B=jackpot*, 4+0=$1,501*, 3+B=$50*, 3+0=$20*, 2+B=$20*, 1+B=$7 fixed, 0+B=$5 fixed. (* pari-mutuel.)
- **Daily 4:** 4 digits 0–9. Mon–Sat, 4 draws/day (Morning 10:00 AM, Day 12:27 PM, Evening 6:00 PM, Night 10:12 PM CT). Wager $0.50/$1. Fireball doubles cost. Fixed prizes per play type (Straight $2,500/$5,000; Box 4/6/12/24-way; Straight/Box; Combo pays as Straight; Pairs $25/$50). Full Fireball payout matrix from `daily4_fireball_prize_chart.pdf` (image PDF — OCR needed to embed exact grid).

*(\* = pari-mutuel; exact amount from the per-draw `details.html` scrape.)*

## 9. Out of scope (v1)

- Email/push notifications (deferred).
- Public/open signup, email verification flows (invite-only for now).
- S3/cloud image storage (local volume; interface ready).
- Materialized views / heavy analytics optimization (YAGNI at this scale).
- Games beyond the five listed.
