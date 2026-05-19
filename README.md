# Fossil — Phylogenic tree of Programming Language Evolution

> An animated phylogenetic tree showing 15 years of programming language evolution,
> driven by a composite health score from GitHub activity, Stack Overflow sentiment,
> job market demand, and academic citations.

---
<img width="1680" height="1050" alt="Screenshot 2026-05-19 at 12 06 58 AM" src="https://github.com/user-attachments/assets/0db3beaf-be1e-4130-a4da-f4602b125f89" />


## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Data Sources                                  │
│  GitHub Archive (BigQuery)  SO Survey CSVs  Adzuna API  Semantic Scholar│
└──────────────────────┬──────────────────────────────────────────────────┘
                       │ Python ingest scripts (Pandas/Django)
                       ▼
              ┌────────────────┐          ┌──────────────────┐
              │   MongoDB       │          │     MySQL         │
              │  (raw events)   │          │  languages +      │
              └───────┬────────┘          │  health_scores    │
                      │ Pub/Sub           │  historical_events│
                      │ raw-events topic  └────────┬──────────┘
                      ▼                            │
         ┌────────────────────────┐                │ Django REST API
         │  Scala Streaming       │                │ (DRF + Channels)
         │  (Akka Streams + ZIO)  │                │
         │  30-day rolling window │                ▼
         │  → score-updates topic │       ┌────────────────┐
         └────────────┬───────────┘       │  Angular SPA   │
                      │ Pub/Sub           │  D3 phylo tree │
                      │ score-updates     │  Time slider   │◄─── WebSocket
                      ▼                  │  Event pins    │     (Django
              ┌───────────────┐          └────────────────┘     Channels)
              │ Django Channels│──────────────────────────────────────────►
              │ WebSocket push │
              └───────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Django 4.2 + Django REST Framework |
| Realtime | Django Channels 4 (ASGI / WebSocket) |
| Database | MySQL 8 (health scores) + MongoDB 7 (raw ingest) |
| Cache / broker | Redis 7 |
| Data pipeline | Pandas + PyMongo |
| Streaming | Scala 2.13, Akka Streams 2.8, ZIO 2 |
| Messaging | Google Cloud Pub/Sub (emulated locally) |
| Frontend | Angular 16, D3.js v7 |
| CI | GitHub Actions |
| GCP | Cloud Run, BigQuery, Cloud Scheduler |
| Analytics | Power BI (`.pbix` in `powerbi/`) |

## Start

```bash
# 1. Clone and copy env template
git clone https://github.com/YOUR_USERNAME/fossil.git && cd fossil
cp .env.example .env          # fill in ADZUNA_APP_ID, ADZUNA_APP_KEY

# 2. (Optional) Add GCP credentials for BigQuery ingest
#    Place your service account JSON at data/gcp-credentials.json

# 3. Start all services
docker compose up --build

# 4. In a separate terminal — run migrations and seed data
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_so      # loads language tree + synthetic scores
docker compose exec backend python manage.py seed_events  # loads historical event annotations

# 5. Open the app
open http://localhost:4200
```

Services started by `docker compose up`:

| Service | Port | Notes |
|---|---|---|
| Angular frontend | 4200 | Live-reload dev server |
| Django backend | 8000 | Daphne ASGI + WebSocket |
| MySQL | 3306 | |
| MongoDB | 27017 | |
| Redis | 6379 | Django Channels layer |
| Pub/Sub emulator | 8085 | Local GCP emulator |
| Scala streaming | — | Subscribes to `raw-events`, publishes to `score-updates` |

## Running the ingest pipeline

```bash
# Ingest all sources for a specific year (requires API keys in .env)
docker compose exec backend python manage.py run_ingest --year 2024

# Ingest a specific source only
docker compose exec backend python manage.py run_ingest --source github --year 2023

# Ingest a date range
docker compose exec backend python manage.py run_ingest --start-year 2020 --end-year 2024
```

## Power BI Report

The Power BI report is at `powerbi/fossil.pbix`. Open it in Power BI Desktop,
then update the BigQuery connection to point at your GCP project.

## GCP Deployment

Config files are committed but deployment is not automated (portfolio demo runs
fully via Docker Compose).

```bash
# Deploy backend to Cloud Run
gcloud run services replace cloudrun/backend.yaml --region=us-central1

# Deploy streaming service
gcloud run services replace cloudrun/streaming.yaml --region=us-central1

# Create BigQuery dataset and table
bq mk --dataset PROJECT_ID:fossil
bq mk --table PROJECT_ID:fossil.health_scores bq/health_scores.json
```

## Project Structure

```
fossil/
├── backend/              Django + DRF + Channels
│   ├── fossil/           settings (base/dev/prod), asgi.py, urls.py
│   ├── languages/        models, views, serializers, consumers, migrations
│   └── ingest/           5 ETL scripts + compute_health_score.py
├── streaming/            Scala streaming service
│   └── src/main/scala/fossil/
│       ├── Main.scala
│       ├── StreamingPipeline.scala
│       ├── PubSubSource.scala
│       └── RollingWindow.scala
├── frontend/             Angular 16 SPA
│   └── src/app/
│       ├── tree/         D3 phylogenetic tree component
│       └── services/     health, websocket, events services
├── data/
│   └── lineage.json      Hand-curated 20-language parent-child tree
├── cloudrun/             Cloud Run service YAMLs
├── bq/                   BigQuery schema files
├── powerbi/              Power BI .pbix report
└── .github/workflows/    GitHub Actions CI
```

