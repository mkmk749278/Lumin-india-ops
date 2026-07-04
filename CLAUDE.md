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
- **Signals** — today's emitted signals with filters
- **Suppressed** — gate rejection telemetry (first stop when "no signals")
- **Outcomes** — TP1/SL/EXPIRED results, net points
- **Quality** — 30-day session summary table

No writes in Phase 1. Control endpoints (kill switch, auto-mode) ship when the
engine has them and Phase 2 execution is activated with owner sign-off.

## Engine API it calls

All endpoints at `https://lumintrade.app` (the India engine VPS):
- `GET /api/health` — liveness
- `GET /api/pulse` — session state, scan count
- `GET /api/signals` — signal list
- `GET /api/suppressed` — gate suppressions
- `GET /api/outcomes` — outcomes (TP1/SL/EXPIRED)
- `GET /api/session-summary` — 30-day quality ledger

## Change-management protocol

Every change via PR. Never push to `main` directly. Auto-merge when CI green.

## Hard limits

- This repo only calls engine endpoints — never modifies engine state directly
- No multi-user, no multi-tenant, no public endpoints
- All routes behind single-password session auth
- Never put secrets in code or `.env.example`

## Secrets needed

Add to GitHub Actions secrets:
- `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` — same as engine repo
- `GH_PAT` — personal access token with repo read
- `INDIA_OPS_SESSION_SECRET` — random 32+ char string
- `INDIA_OPS_AUTH_TOKEN` — the ops dashboard login password
- `API_STATIC_TOKEN` — same as the engine's `API_STATIC_TOKEN`

## Commands

```bash
# Local dev
OPS_SESSION_SECRET=dev OPS_AUTH_TOKEN=dev uvicorn app.main:app --reload --port 8080

# Tests
pytest -q

# Docker
docker compose --env-file .env up --build
```

## Conventions

- FastAPI async throughout — no blocking I/O in routes
- Templates extend `base.html`; `login.html` is standalone
- Templates render unknown API payload shapes gracefully (check for `error` key first)
- The engine is source of truth — ops never caches or stores data locally
