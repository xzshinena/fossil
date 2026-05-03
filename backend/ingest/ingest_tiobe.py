"""
Ingest TIOBE Index rankings via RSS feed.

Scrapes current top-20 from https://www.tiobe.com/tiobe-index/rss.xml.
Only the current month is available without a paid subscription;
all other months are left with no TIOBE source (partial=True in composite).

Run standalone:
  DJANGO_SETTINGS_MODULE=fossil.settings.dev python -m ingest.ingest_tiobe
"""
import logging
import os
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TIOBE_RSS = 'https://www.tiobe.com/tiobe-index/rss.xml'
TIOBE_INDEX = 'https://www.tiobe.com/tiobe-index/'

LANGUAGES = {
    'python', 'javascript', 'typescript', 'java', 'c', 'c++', 'go',
    'rust', 'kotlin', 'swift', 'scala', 'ruby', 'php', 'perl',
    'haskell', 'r', 'julia', 'fortran', 'cobol', 'lisp',
}

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; fossil-research-bot/1.0)'}


def _rank_to_score(rank: int, total: int = 20) -> float:
    """Convert a 1-based rank to a 0-100 score (rank 1 → 100, rank 20 → ~0)."""
    return round(max(0.0, (total - rank + 1) / total * 100), 2)


def _fetch_current_rankings() -> dict[str, float]:
    """Return {language_lower: score} for current TIOBE top-20."""
    rankings: dict[str, float] = {}

    # Try RSS first (cleaner to parse)
    try:
        resp = requests.get(TIOBE_RSS, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'xml')
        items = soup.find_all('item')
        rank = 1
        for item in items:
            title = item.find('title')
            if not title:
                continue
            lang = title.text.strip().lower()
            if lang in LANGUAGES:
                rankings[lang] = _rank_to_score(rank)
            rank += 1
        if rankings:
            logger.info('TIOBE RSS: found %d matching languages', len(rankings))
            return rankings
    except Exception as exc:
        logger.warning('TIOBE RSS failed: %s — falling back to HTML', exc)

    # Fallback: scrape the main index HTML table
    try:
        resp = requests.get(TIOBE_INDEX, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', {'id': 'top20'})
        if not table:
            table = soup.find('table')
        if table:
            rows = table.find_all('tr')[1:]  # skip header
            for i, row in enumerate(rows[:20], start=1):
                cells = row.find_all('td')
                if len(cells) >= 5:
                    lang = cells[4].text.strip().lower()
                    if lang in LANGUAGES:
                        rankings[lang] = _rank_to_score(i)
        logger.info('TIOBE HTML: found %d matching languages', len(rankings))
    except Exception as exc:
        logger.error('TIOBE HTML scrape failed: %s', exc)

    return rankings


def run() -> int:
    from ingest.mongo_client import upsert_raw
    from ingest.pubsub_client import publish_raw_event
    from languages.models import Language

    lang_id_map = {lang.name.lower(): lang.id for lang in Language.objects.all()}
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month

    rankings = _fetch_current_rankings()
    if not rankings:
        logger.error('TIOBE: no rankings fetched, aborting')
        return 0

    total = 0
    for lang, score in rankings.items():
        upsert_raw(
            source='tiobe',
            language=lang,
            year=year,
            month=month,
            raw_value=score,
        )
        publish_raw_event(
            source='tiobe',
            language=lang,
            year=year,
            month=month,
            raw_value=score,
            language_id=lang_id_map.get(lang),
        )
        total += 1

    logger.info('TIOBE ingest complete: %d rows (current month %d-%02d only)', total, year, month)
    return total


if __name__ == '__main__':
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fossil.settings.dev')
    django.setup()
    logging.basicConfig(level=logging.INFO)
    run()
