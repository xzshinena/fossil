# Project Overview
Fossil is a full-stack data engineering and visualization platform that tracks the health, popularity, and evolutionary relationships of programming languages over time. It ingests data from multiple real-world sources (GitHub, Stack Overflow, job boards, academic papers), computes a composite Language Health Score per language per month, and renders the results as an interactive phylogenetic tree where users can watch the entire history of programming languages play out on a timeline scrubber.
The project is intentionally ambitious: it has a real-time streaming layer, a batch ETL pipeline, two database backends, a cloud-native deployment, an analytical BI layer, and a rich interactive frontend.

## Tech Stack (Non-Negotiable)
Layer Technology
API Server Python, Django, Django REST Framework
Batch ETL Pandas
Streaming Pipeline Scala, Akka Streams, ZIO, Cats, Monix
Primary DB MySQLRaw 
Data Store MongoDB
Cloud Google Cloud Platform (Cloud Run, Pub/Sub, BigQuery, Cloud Scheduler, Cloud Storage)
Frontend Angular, TypeScript, JavaScript, D3.jsBI / 
Reporting Power BI (connected to BigQuery)

## Data Sources
Pull from the following public sources:

GitHub API — repository counts, commit activity, and star trends per language
Stack Overflow Developer Survey CSVs — published annually since 2011, tracks language usage and satisfaction
TIOBE / PYPL index — monthly language popularity rankings (scrape or RSS)
Semantic Scholar / arXiv API — academic paper metadata to track research adoption
Indeed / LinkedIn scraper — job posting frequency per language over time

Each source produces a sub-score. Pandas normalizes and weights them into a single composite Health Score (0–100) per language per month stored in MySQL.

## System Architecture
[GitHub API] [SO CSVs] [Job Scraper] [arXiv API] [TIOBE]
      |             |          |            |          |
      └─────────────┴──────────┴────────────┴──────────┘
                              |
                    [GCP Cloud Pub/Sub]
                    /                  \
    [Scala Streaming Service]     [GCP Cloud Storage]
    (Akka/ZIO/Cats/Monix)              |
           |                    [Pandas ETL Pipeline]
    [MongoDB - Raw Store]              |
                    \           [MySQL - Health Scores]
                     \                 |
                      └──────[Django REST API]──────┘
                                      |
                             [Angular Frontend]
                            /         |          \
                      Tree View  Timeline      Graveyard
                                      |
                             [GCP BigQuery]
                                      |
                             [Power BI Reports]


## Notes

Start every new module by writing tests first where possible
Use environment variables for all credentials — never hardcode
Django settings should have separate dev.py and prod.py configs
The Scala service and Django API should communicate only via Pub/Sub and shared databases — never direct HTTP between them
D3.js tree rendering should be encapsulated in a single Angular service so the component stays clean
All Pandas pipeline steps should be independently runnable and idempotent