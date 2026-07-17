# CLAUDE.md — lumin-india-ops

Operational brief for CTE sessions in this repository.

## Role

CTE with full technical ownership. This is the owner-only diagnostic dashboard
for the Lumin India NSE F&O signal engine.

Before every session read in order:
1. `OWNER_BRIEF.md` in lumina-india-engine
2. `ACTIVE_CONTEXT.md` in lumina-india-engine

## Scope

Read-only diagnostic dashboard in Phase 1. Views:
- **Pulse** — engine session state, scan count, uptime
- **Signals** — emitted signals over a date range (presets + custom from/to),
  with per-signal outcome and a full CSV download
- **Suppressed** — gate rejection telemetry (first stop when "no signals")
- **Outcomes** — per-signal results under the engine's two-target plan
  (SL_HIT / TP1_HIT / TP1_BE / TP2_HIT / TP1_EXPIRED / EXPIRED), net %.
  Every TP1-banked outcome counts as a win; `result_pct` arrives
  position-weighted from the engine — ops does no leg math.
  **`NOT_TRIGGERED`** (entry-trigger plan, Session 21: a LEVEL entry that
  never filled) is surfaced as its own count and excluded from every
  win/EV denominator (`app/routes/outcomes.py`); an `ambiguous_tie`
  ledger-health count flags both-levels-in-one-candle resolutions
- **Edge** — the engine's Strategy×Context edge matrix (`/api/edge-matrix`):
  realised win% / net% / cost-adjusted expectancy per setup, tier, session
  phase, VIX regime, and market-direction-vs-signal cohort, plus the
  Session-21 truth-telemetry dimensions (extension-at-entry bucket,
  duplicate ordinal) and a `context_excluded` counter for segregated
  pre-migration rows. Read-only view of measured edge (the surface the
  tier recalibration + allocator read)
- **Allocator** — the engine's observe-only strategy recommendations
  (`/api/allocator`): per-cohort EMIT / SUPPRESS / HOLD / INSUFFICIENT_DATA
  verdicts from measured edge. Recommendation mode — shows "what it would do",
  changes nothing the engine emits
- **Quality** — 30-day session summary table
- **Strategy** — signal-quality lab: filter resolved signals by tier / setup /
  side / base / min-confidence / min-RR over a window and read the realised
  win-rate, net %, expectancy and profit factor, with best-first breakdowns and
  a cohort CSV download
- **Control** — owner maintenance panel (owner-directed, Session 15): clear
  signal history (all / today, requires typing CLEAR) and reset today's
  in-memory gate state. Actions are executed by the engine via its
  static-token-only `/api/admin/*` endpoints — ops still never touches engine
  state directly. No trading controls here until Phase 2 sign-off.

Date-range views work by fanning out the engine's single-date `/api/signals`
across each day in the window (concurrent, capped at 92 days) and aggregating in
the ops layer — no local storage, engine stays source of truth.

Diagnostics are read-only; the Control view carries owner *maintenance*
writes only (history wipe, gate reset). Trading controls (kill switch,
auto-mode) ship when the engine has them and Phase 2 execution is activated
with owner sign-off.

## Engine API it calls

All endpoints at `https://lumintrade.app` (the India engine VPS):
- `GET /api/health` — liveness
- `GET /api/pulse` — session state, scan count
- `GET /api/signals` — signal list
- `GET /api/suppressed` — gate suppressions
- `GET /api/outcomes` — outcomes (two-target plan statuses + walk telemetry)
- `GET /api/session-summary` — 30-day quality ledger
- `GET /api/edge-matrix?days=` — Strategy×Context edge matrix (Edge view)
- `GET /api/allocator?days=` — observe-only allocator verdicts (Allocator view)
- `POST /api/admin/clear-history` — wipe signal history (Control view)
- `POST /api/admin/reset-gates` — reset today's in-memory gate state

Client: `app/data_sources/engine_api.py` (async httpx, bearer token). The
date-range fan-out lives in `signals_range()` there; range resolution/clamping
(92-day cap, IST) in `app/ranges.py`.

## Change-management protocol

Every change via PR. Never push to `main` directly. Auto-merge when CI green.

## Hard limits

- This repo only calls engine endpoints — never modifies engine state directly
- No multi-user, no multi-tenant, no public endpoints
- All routes behind single-password session auth
- Never put secrets in code or `.env.example`

## Secrets & runtime env vars

GitHub Actions secrets:
- `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` — same as engine repo
- `GH_PAT` — personal access token with repo read
- `INDIA_OPS_SESSION_SECRET` — random 32+ char string
- `INDIA_OPS_AUTH_TOKEN` — the ops dashboard login password
- `API_STATIC_TOKEN` — same as the engine's `API_STATIC_TOKEN`

The app itself (`app/config.py`) reads **runtime** env vars — `deploy.yml`
maps the secrets onto these at deploy time:
- `OPS_SESSION_SECRET` ← `INDIA_OPS_SESSION_SECRET`
- `OPS_AUTH_TOKEN` ← `INDIA_OPS_AUTH_TOKEN`
- `INDIA_ENGINE_API_BASE` — engine base URL (default `https://lumintrade.app`)
- `INDIA_API_TOKEN` ← `API_STATIC_TOKEN` (bearer for engine calls)
- `OPS_PORT` (default 8080), `LOG_LEVEL`

Note: `deploy.yml` has `paths-ignore` for `*.md` — doc-only merges do not
trigger a redeploy.

## Commands

```bash
# Local dev
OPS_SESSION_SECRET=dev OPS_AUTH_TOKEN=dev uvicorn app.main:app --reload --port 8080

# Tests
pytest -q

# Lint (CI runs this too)
ruff check app/

# Docker
docker compose --env-file .env up --build
```

## Layout

- `app/main.py` — FastAPI app, SessionMiddleware + `AuthRedirectMiddleware`
  (`app/auth_mw.py`; public paths: `/login`, `/logout`, `/healthz`, `/static`),
  router registration, `GET /healthz` liveness
- `app/routes/` — one module per view (`pulse.py`, `signals.py`, `suppressed.py`,
  `outcomes.py`, `quality.py`, `strategy.py`, `edge.py`, `allocator.py`,
  `control.py`, `auth.py`); templates 1:1 in `app/templates/`
- `app/analytics.py` — pure signal-quality math behind Strategy (win rate,
  net %, expectancy, profit factor, breakdowns)
- `app/exports.py` — fixed 24-column `SIGNAL_FIELDS` CSV schema used by the
  Signals and Strategy exports
- `tests/` — `test_app.py` (auth redirect + route smoke), `test_control.py`
  (admin proxy against a fake engine), `test_analytics.py`

## Conventions

- FastAPI async throughout — no blocking I/O in routes
- Templates extend `base.html`; `login.html` is standalone
- Templates render unknown API payload shapes gracefully (check for `error` key first)
- The engine is source of truth — ops never caches or stores data locally
