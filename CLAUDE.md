# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Two-week upskilling project: end-to-end visualisation of oil-carrying tankers in Philippine waters on GCP. The pipeline reads AIS positions from AISStream.io, filters to tanker ship types, enriches against an IMO vessel master, stores positions in Cloud SQL Postgres, and serves them through a FastAPI Cloud Run service to a React/Vite frontend hosted on GitHub Pages.

## Layout

- `backend/` — single Python package, single Docker image, **three entrypoints**:
  - `api/` — FastAPI app (default `CMD` in [backend/Dockerfile](backend/Dockerfile))
  - `ingestor/` — Cloud Run **Job**, invoked as `python -m ingestor.main` (Cloud Run Job overrides the image's CMD)
  - `bootstrap/load_vessel_master.py` — one-off CSV loader, run manually via Cloud SQL Auth Proxy
  - `shared/` — DB engine, schema DDL, cargo estimator, shared by all three
- `frontend/` — React + Vite + TypeScript, deployed to GitHub Pages
- `infra/` — Terraform (Google provider `~> 6.0`); 11 `.tf` files, ~32 resources
- `.github/workflows/` — `deploy-backend.yml` (Cloud Run via WIF) and `deploy-frontend.yml` (Pages)

## Commands

All paths relative to repo root unless noted.

### Backend

```powershell
# Install (editable + dev deps), from backend/
pip install -e ".[dev]"

# Run API locally — requires DATABASE_URL (Cloud SQL Auth Proxy on 5432 works)
$env:DATABASE_URL="postgresql+pg8000://tankers_app:<pw>@localhost:5432/tankers"
uvicorn api.main:app --reload --port 8080

# Run ingestor locally (45-min capture by default; lower for testing)
$env:AISSTREAM_API_KEY="..."; $env:CAPTURE_MINUTES="2"
python -m ingestor.main

# Load vessel master CSV (IMO GISIS export, columns documented in load_vessel_master.py)
python -m bootstrap.load_vessel_master backend/bootstrap/data/tankers_master.csv

# Lint
ruff check .
```

### Frontend (from `frontend/`)

```powershell
npm install
npm run dev       # vite dev server on :5173
npm run build     # tsc -b && vite build → dist/
npm run lint      # tsc -b --noEmit (typecheck only; there is no ESLint config)
npm run preview   # serve built dist/
```

Required env (copy `frontend/.env.example` → `frontend/.env.local`): `VITE_GOOGLE_MAPS_API_KEY`, `VITE_API_BASE_URL`.

### Infrastructure (from `infra/`)

```powershell
terraform init
terraform plan
terraform apply
```

PowerShell mangles `-out=tfplan.binary` ("Too many command line arguments" / "The '<' operator is reserved"). Use bare `terraform plan` or quote: `terraform plan "-out=tfplan.binary"`.

### Docker (from `backend/`)

```powershell
docker build -t oiltank-ph-backend .
# Override CMD to run the ingestor instead of the API
docker run --rm oiltank-ph-backend python -m ingestor.main
```

### Operating the deployed system

```powershell
# Manually trigger the daily ingest
gcloud run jobs execute oiltank-ph-ingestor --region=asia-southeast1 --wait

# Tail logs
gcloud run services logs read oiltank-ph-api --region=asia-southeast1 --limit=100
gcloud run jobs logs read oiltank-ph-ingestor --region=asia-southeast1 --limit=200

# Stop / start SQL (saves ~70% while stopped)
gcloud sql instances patch oiltank-ph-pg --activation-policy=NEVER
gcloud sql instances patch oiltank-ph-pg --activation-policy=ALWAYS
```

## Architecture notes worth knowing before editing

### DB connection has two modes

`shared/db.py:build_engine` dispatches on env vars:
- `DB_INSTANCE_CONNECTION_NAME` set → Cloud SQL Python Connector + pg8000 + IAM-attached SA (production path on Cloud Run)
- Else `DATABASE_URL` set → plain SQLAlchemy URL (local dev / Cloud SQL Auth Proxy)
- Neither → raises

Engine + sessionmaker are module-level singletons built lazily on first call to `get_engine()`.

### Ingestion is stateful within a run

`ingestor/main.py` keeps a per-MMSI `StaticInfo` cache from `ShipStaticData` messages and only emits a position row when the cached `ship_type ∈ {80..89}` (broad tanker filter). A `PositionReport` arriving **before** the matching static frame is dropped — this is by design; AISStream replays static frames frequently enough. The flag is also derived from the MMSI MID prefix with a small in-file lookup (`mmsi_to_flag`).

Batches flush every 1000 positions **or** 300 s, whichever first; a final flush runs at end-of-capture. The Enricher (`ingestor/enrich.py`) caches IMO→subtype lookups for the lifetime of the run.

### Schema lives in `backend/shared/schema.sql` and is applied idempotently

Both ingestor `main.py` and `bootstrap/load_vessel_master.py` call `apply_schema()` on startup — it splits on `;` and executes each statement, all `CREATE … IF NOT EXISTS`. There is no Alembic. To evolve the schema, edit `schema.sql` and write any migration DDL alongside in the same file (must stay idempotent) or run ad-hoc SQL via the Auth Proxy.

Three tables: `vessel_master` (slowly-changing, loaded from CSV), `vessels` (per-MMSI hot state, upserted by ingestor), `positions` (append-only, unique on `(mmsi, reported_at)`).

### Cargo tonnage is **estimated**, not observed

Formula in `shared/estimator.py`: `tonnes = dwt * clamp(current_draught / design_draught, 0, 1)`. UI must label this "Estimated" (see [frontend/src/components/VesselPanel.tsx](frontend/src/components/VesselPanel.tsx)). Confidence string returned alongside: `high` / `medium` / `low` / `none`.

### Subtype enum is fixed in three places

`crude_oil | product | chemical | lng | lpg | other | unknown` — declared in `api/routes.py:ALL_SUBTYPES`, normalised on bootstrap in `bootstrap/load_vessel_master.py:SUBTYPE_MAP`, and rendered in [frontend/src/components/SubtypeFilter.tsx](frontend/src/components/SubtypeFilter.tsx). Default UI filter is `crude_oil,product` (`api/routes.py:DEFAULT_OIL_SUBTYPES`). Adding a subtype means editing all three plus the SQL won't reject it (subtype is `TEXT`, not an enum type).

### Cloud Run images are placeholders in Terraform

[infra/run_api.tf](infra/run_api.tf) and [infra/run_job.tf](infra/run_job.tf) use `gcr.io/cloudrun/hello` and both have `lifecycle.ignore_changes = [..containers[0].image]`. CI deploys the real image via `gcloud run deploy` / `gcloud run jobs update`, and Terraform won't try to revert it.

`deletion_protection = false` on the Cloud SQL instance is intentional (dev project, easy teardown). Cloud Run service/job default `deletion_protection = true`.

### API is public (`allUsers` `roles/run.invoker`)

The frontend on GitHub Pages calls the API unauthenticated. CORS allowlist comes from `FRONTEND_ORIGIN` env var (set from `var.frontend_origin` in Terraform). **GitHub Pages serves at the lowercased username**, so `frontend_origin` in `terraform.tfvars` must be lowercase or the browser will be blocked.

### Frontend base path is repo-name-aware

[frontend/vite.config.ts](frontend/vite.config.ts) reads `BASE_PATH`; the GitHub Actions workflow sets it to `/${{ github.event.repository.name }}/` so the built `index.html` references assets correctly. Local `npm run dev` uses `/`.

## CI / deploy

- **`deploy-backend.yml`** triggers on `backend/**` or workflow change. Uses Workload Identity Federation (`google-github-actions/auth@v2`) — no JSON SA key. Builds the single image, pushes to Artifact Registry, then `gcloud run deploy` (API) **and** `gcloud run jobs update` (ingestor) with the same image tag. Required repo secrets: `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SA`.
- **`deploy-frontend.yml`** triggers on `frontend/**`. Builds with `VITE_API_BASE_URL` and `VITE_GOOGLE_MAPS_API_KEY` from repo secrets, deploys `frontend/dist` to GitHub Pages.

## Local state of the project

No tests exist. The backend has `pytest` as a dev dep but zero test files. Plan-of-record document lives at `C:\Users\cholo\.claude\plans\i-want-to-make-splendid-crown.md` — defer to it for architecture rationale.

[PROGRESS.md](PROGRESS.md) is a living progress log: current phase, what's done, next steps, decisions, gotchas. **Read it at the start of every session and update it when something meaningful changes.**
