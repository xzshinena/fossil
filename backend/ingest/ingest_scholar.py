"""
Ingest academic citation counts from Semantic Scholar API.

Rate limits: 100 req/5 min without key, ~1 req/sec with key.
Set SEMANTIC_SCHOLAR_API_KEY env var to increase limits.

Fetches paper counts per language per year (2011-2024).
Months within a year all receive the same annual value (surveys are annual).

Run standalone:
  DJANGO_SETTINGS_MODULE=fossil.settings.dev python -m ingest.ingest_scholar
"""
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

API_BASE = 'https://api.semanticscholar.org/graph/v1'
API_KEY = os.environ.get('SEMANTIC_SCHOLAR_API_KEY', '')

# Search queries per language (some need specific terms to avoid noise)
LANG_QUERIES: dict[str, str] = {
    'python': 'Python programming language',
    'javascript': 'JavaScript programming language',
    'typescript': 'TypeScript programming language',
    'java': 'Java programming language',
    'c': 'C programming language systems',
    'c++': 'C++ programming language',
    'go': 'Go golang programming language',
    'rust': 'Rust programming language memory safety',
    'kotlin': 'Kotlin programming language Android',
    'swift': 'Swift programming language Apple iOS',
    'scala': 'Scala programming language functional',
    'ruby': 'Ruby programming language Rails',
    'php': 'PHP web programming language',
    'perl': 'Perl programming language',
    'haskell': 'Haskell functional programming language',
    'r': 'R statistical programming language',
    'julia': 'Julia scientific programming language',
    'fortran': 'Fortran scientific programming language',
    'cobol': 'COBOL programming language',
    'lisp': 'Lisp programming language',
}

# Delay between requests (seconds). Increases if no API key.
REQUEST_DELAY = 0.5 if API_KEY else 3.5


def _search_papers(query: str, year: int) -> int:
    """Return paper count matching query published in the given year."""
    params = {
        'query': query,
        'year': str(year),
        'limit': 1,
        'fields': 'year',
    }
    headers = {'x-api-key': API_KEY} if API_KEY else {}

    try:
        resp = requests.get(
            f'{API_BASE}/paper/search',
            params=params,
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 429:
            logger.warning('Scholar rate limited — sleeping 60s')
            time.sleep(60)
            return _search_papers(query, year)
        resp.raise_for_status()
        data = resp.json()
        return data.get('total', 0)
    except requests.RequestException as exc:
        logger.error('Scholar API error for %r year %d: %s', query, year, exc)
        return 0


def run(start_year: int = 2011, end_year: int = 2024) -> int:
    from ingest.mongo_client import upsert_raw
    from ingest.pubsub_client import publish_raw_event
    from languages.models import Language

    lang_id_map = {lang.name.lower(): lang.id for lang in Language.objects.all()}
    total = 0

    for lang_lower, query in LANG_QUERIES.items():
        logger.info('Scholar: fetching citations for %s', lang_lower)
        for year in range(start_year, end_year + 1):
            count = _search_papers(query, year)
            if count == 0:
                time.sleep(REQUEST_DELAY)
                continue

            for month in range(1, 13):
                upsert_raw(
                    source='scholar',
                    language=lang_lower,
                    year=year,
                    month=month,
                    raw_value=float(count),
                )
                publish_raw_event(
                    source='scholar',
                    language=lang_lower,
                    year=year,
                    month=month,
                    raw_value=float(count),
                    language_id=lang_id_map.get(lang_lower),
                )
                total += 1

            time.sleep(REQUEST_DELAY)

    logger.info('Scholar ingest complete: %d total rows', total)
    return total


if __name__ == '__main__':
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fossil.settings.dev')
    django.setup()
    logging.basicConfig(level=logging.INFO)
    run()
