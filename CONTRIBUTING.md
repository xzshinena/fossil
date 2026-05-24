# Contributing to Fossil

Thanks for your interest in contributing! This guide gets you from zero to a running dev environment.

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Docker Desktop | Latest | https://docs.docker.com/get-docker/ |
| Git | Any | https://git-scm.com |
| Make | Any | Pre-installed on macOS/Linux. Windows: use WSL2 or Git Bash |

You do **not** need Node, Python, Java, or Scala installed locally — everything runs inside Docker.

## Quick start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/fossil.git
cd fossil

# 2. Copy the env template (no keys required to run the app)
cp .env.example .env

# 3. Build and start everything — migrations and seed data run automatically
make setup

# 4. Open the app
open http://localhost:4200
```

`make setup` takes 3–5 minutes on first run (Docker pulls images and builds). Subsequent runs are faster.

## What's running

| Service | URL | What it is |
|---|---|---|
| Frontend | http://localhost:4200 | Angular dev server with live reload |
| Backend API | http://localhost:8000 | Django REST + WebSocket |
| MySQL | localhost:3306 | Primary database |
| MongoDB | localhost:27017 | Raw ingest store |
| Redis | localhost:6379 | WebSocket channel layer |
| Pub/Sub emulator | localhost:8085 | Local GCP messaging |

## Common commands

```bash
make dev     # Start services without rebuilding
make down    # Stop all services
make seed    # Re-run migrations and seed data
make test    # Run backend (pytest) and frontend (Karma) tests
make logs    # Tail logs for all services
make shell   # Open a Django shell
```

## Optional: API keys

The app runs fully without external API keys. Keys are only needed if you want to re-run the data ingest pipeline:

| Key | Where to get it | What it unlocks |
|---|---|---|
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | https://developer.adzuna.com | Job market data |
| `SEMANTIC_SCHOLAR_API_KEY` | https://semanticscholar.org/product/api | Academic citation data |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP service account JSON | BigQuery + GitHub Archive |

Add keys to your `.env` file, then run `make seed` to ingest.

## Project structure

```
fossil/
├── backend/          Django API + WebSocket (Python)
│   ├── fossil/       Settings, ASGI config
│   ├── languages/    Models, views, serializers, consumers
│   └── ingest/       ETL scripts
├── frontend/         Angular SPA + D3 tree (TypeScript)
├── streaming/        Real-time score pipeline (Scala)
├── data/             lineage.json — hand-curated language tree
├── bq/               BigQuery schemas
└── cloudrun/         GCP deployment configs
```

## Where to start

Not sure what to work on? Good entry points:

- **Frontend / D3 visualization** — `frontend/src/app/tree/` — no backend changes needed, hot-reloads instantly
- **REST API / models** — `backend/languages/` — add an endpoint, fix a serializer
- **Data / seeding** — `backend/languages/management/commands/` — improve seed data or add a new source
- **Docs / tests** — always welcome

## Troubleshooting

**`make setup` hangs waiting for the database**
MySQL can take 30–60 seconds on first boot. If it never resolves, run `make logs` in another terminal to see what's failing.

**Port already in use**
Something on your machine is using 4200, 8000, 3306, 27017, or 6379. Stop the conflicting process or edit the port mappings in `docker-compose.yml`.

**Frontend shows a blank page or network error**
The backend might still be starting up. Wait 10–15 seconds and refresh. Check `make logs` for backend errors.

**I changed a Python dependency**
Rebuild the backend image: `docker compose build backend`, then `make dev`.

**I need to reset everything**
```bash
make down
docker compose down -v   # removes volumes (database data)
make setup
```

## Pull request checklist

- [ ] `make test` passes locally
- [ ] New endpoints have at least a basic test in `backend/languages/tests/`
- [ ] No `.env` values or credentials committed
- [ ] PR description explains *why*, not just *what*
