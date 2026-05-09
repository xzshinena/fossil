"""
Export MySQL health_scores to BigQuery for Power BI consumption.

Usage:
  python manage.py export_to_bq
  python manage.py export_to_bq --dataset fossil --table health_scores
  python manage.py export_to_bq --dry-run

The BigQuery table is created from bq/health_scores.json if it doesn't exist.
Each run truncates and reloads all rows (3,360 rows; WRITE_TRUNCATE is safe).
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand

from languages.models import HealthScore

BQ_DATASET = os.environ.get('BQ_DATASET', 'fossil')
BQ_TABLE = os.environ.get('BQ_TABLE', 'health_scores')
BQ_PROJECT = os.environ.get('BQ_PROJECT', os.environ.get('PUBSUB_PROJECT_ID', 'fossil-dev'))

# Maps source_breakdown JSON keys → BigQuery column names.
# Key order matters: first match wins (so "so" checked before "so_synthetic").
SOURCE_KEY_MAP = {
    'so_score':        ['so'],
    'github_score':    ['github'],
    'jobs_score':      ['jobs', 'adzuna'],
    'citations_score': ['citations', 'scholar'],
}


def _extract_sub_score(breakdown: dict, bq_col: str) -> float | None:
    for key in SOURCE_KEY_MAP[bq_col]:
        if key in breakdown:
            return breakdown[key]
    return None


class Command(BaseCommand):
    help = 'Export health_scores from MySQL to BigQuery (WRITE_TRUNCATE)'

    def add_arguments(self, parser):
        parser.add_argument('--dataset', default=BQ_DATASET)
        parser.add_argument('--table', default=BQ_TABLE)
        parser.add_argument('--project', default=BQ_PROJECT)
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Print row count and first row without writing to BigQuery',
        )

    def handle(self, *args, **options):
        from google.cloud import bigquery

        dataset_id = options['dataset']
        table_id = options['table']
        project = options['project']
        dry_run = options['dry_run']

        ingested_at = datetime.now(tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        qs = HealthScore.objects.select_related('language').order_by(
            'language__name', 'year', 'month'
        )

        rows = []
        for hs in qs:
            bd = hs.source_breakdown or {}
            rows.append({
                'language_id':      hs.language_id,
                'language_name':    hs.language.name,
                'year':             hs.year,
                'month':            hs.month,
                'score':            hs.score,
                'partial':          hs.partial,
                'so_score':         _extract_sub_score(bd, 'so_score'),
                'github_score':     _extract_sub_score(bd, 'github_score'),
                'jobs_score':       _extract_sub_score(bd, 'jobs_score'),
                'citations_score':  _extract_sub_score(bd, 'citations_score'),
                'ingested_at':      ingested_at,
            })

        if dry_run:
            self.stdout.write(f'Dry run: {len(rows)} rows')
            if rows:
                self.stdout.write(json.dumps(rows[0], indent=2))
            return

        client = bigquery.Client(project=project)
        table_ref = f'{project}.{dataset_id}.{table_id}'

        # parents[3] = /app (Docker) or .../fossil/backend (local); bq/ is a sibling of backend/
        base = Path(__file__).resolve().parents[3]
        schema_path = base / 'bq' / 'health_scores.json'
        if not schema_path.exists():
            schema_path = base.parent / 'bq' / 'health_scores.json'
        with open(schema_path) as f:
            raw_schema = json.load(f)
        bq_schema = [bigquery.SchemaField.from_api_repr(col) for col in raw_schema]

        table = bigquery.Table(table_ref, schema=bq_schema)
        client.create_table(table, exists_ok=True)

        job_config = bigquery.LoadJobConfig(
            schema=bq_schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        )
        job = client.load_table_from_json(rows, table_ref, job_config=job_config)
        job.result()

        dest = job.destination
        self.stdout.write(self.style.SUCCESS(
            f'Loaded {len(rows)} rows → {dest.project}.{dest.dataset_id}.{dest.table_id}'
        ))
