"""
Ingest GitHub activity from BigQuery githubarchive.month.* public dataset.

Queries PushEvent counts per language per month for 2011-2024.
Writes raw counts to MongoDB then publishes to Pub/Sub raw-events.

Run standalone:
  DJANGO_SETTINGS_MODULE=fossil.settings.dev python -m ingest.ingest_github
"""
import logging
import os
import sys

logger = logging.getLogger(__name__)

LANGUAGES = [
    'Python', 'JavaScript', 'TypeScript', 'Java', 'C', 'C++', 'Go',
    'Rust', 'Kotlin', 'Swift', 'Scala', 'Ruby', 'PHP', 'Perl',
    'Haskell', 'R', 'Julia', 'Fortran', 'COBOL', 'Lisp',
]

# BigQuery scans one year at a time to keep costs low
START_YEAR = 2011
END_YEAR = 2024


def run(start_year: int = START_YEAR, end_year: int = END_YEAR) -> int:
    from google.cloud import bigquery
    from google.api_core.exceptions import DeadlineExceeded, GoogleAPIError
    from ingest.mongo_client import upsert_raw
    from ingest.pubsub_client import publish_raw_event
    from languages.models import Language

    lang_id_map = {lang.name.lower(): lang.id for lang in Language.objects.all()}
    client = bigquery.Client()
    lang_list = ', '.join(f"'{l.lower()}'" for l in LANGUAGES)
    total = 0

    for year in range(start_year, end_year + 1):
        suffix_start = f'{year}01'
        suffix_end = f'{year}12'

        query = f"""
            SELECT
              LOWER(JSON_VALUE(payload, '$.repository.language')) AS language,
              EXTRACT(YEAR FROM created_at) AS year,
              EXTRACT(MONTH FROM created_at) AS month,
              COUNT(*) AS push_count
            FROM `githubarchive.month.*`
            WHERE
              _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
              AND type = 'PushEvent'
              AND LOWER(JSON_VALUE(payload, '$.repository.language'))
                  IN ({lang_list})
            GROUP BY language, year, month
            ORDER BY language, year, month
        """

        job_config = bigquery.QueryJobConfig(
            use_query_cache=True,
            maximum_bytes_billed=10 * 1024 ** 3,  # 10 GB safety cap
        )

        try:
            logger.info('querying BigQuery for year %d', year)
            job = client.query(query, job_config=job_config)
            rows = job.result(timeout=120)
        except DeadlineExceeded:
            logger.error('BigQuery timeout for year %d — skipping, marking partial', year)
            continue
        except GoogleAPIError as exc:
            logger.error('BigQuery error for year %d: %s', year, exc)
            continue

        for row in rows:
            if not row.language or row.push_count is None:
                continue
            doc = upsert_raw(
                source='github',
                language=row.language,
                year=int(row.year),
                month=int(row.month),
                raw_value=float(row.push_count),
            )
            publish_raw_event(
                source='github',
                language=row.language,
                year=int(row.year),
                month=int(row.month),
                raw_value=float(row.push_count),
                language_id=lang_id_map.get(row.language),
            )
            total += 1

        logger.info('year %d: ingested %d github rows so far', year, total)

    logger.info('github ingest complete: %d total rows', total)
    return total


if __name__ == '__main__':
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fossil.settings.dev')
    django.setup()
    logging.basicConfig(level=logging.INFO)
    run()
