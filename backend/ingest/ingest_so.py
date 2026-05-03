"""
Ingest Stack Overflow Developer Survey data.

Reads annual CSVs from data/so_surveys/<year>.csv (2011-2024).
Extracts Admired % per language using per-year column mapping.
Fills all 12 months with the annual value (surveys are annual snapshots).

Pre-2015 column mapping per TODOS.md TODO-1:
  2011 — no admired column; skip
  2012 — tech_use
  2013 — have_tech
  2014 — loved

Run standalone:
  DJANGO_SETTINGS_MODULE=fossil.settings.dev python -m ingest.ingest_so
"""
import logging
import os
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

SO_COLUMN_MAP: dict[int, str | None] = {
    2011: None,
    2012: 'tech_use',
    2013: 'have_tech',
    2014: 'loved',
}

ADMIRED_CANDIDATES = [
    'LanguageWantToWorkWith', 'LanguageDesireNextYear',
    'HaveWorkedLanguage', 'AdmiredLanguage',
]

LANGUAGES = [
    'Python', 'JavaScript', 'TypeScript', 'Java', 'C', 'C++', 'Go',
    'Rust', 'Kotlin', 'Swift', 'Scala', 'Ruby', 'PHP', 'Perl',
    'Haskell', 'R', 'Julia', 'Fortran', 'COBOL', 'Lisp',
]


def _detect_column(df: pd.DataFrame, year: int) -> str | None:
    if year in SO_COLUMN_MAP:
        return SO_COLUMN_MAP[year]
    for candidate in ADMIRED_CANDIDATES:
        if candidate in df.columns:
            return candidate
    return None


def _score_for_language(df: pd.DataFrame, col: str, lang: str) -> float | None:
    try:
        hits = df[col].dropna().astype(str)
        total = len(hits)
        if total == 0:
            return None
        matches = hits.str.contains(lang, case=False, regex=False).sum()
        return round((matches / total) * 100, 2)
    except Exception as exc:
        logger.warning('SO score extraction failed for %s/%s: %s', lang, col, exc)
        return None


def run(surveys_dir: Path | None = None) -> int:
    from ingest.mongo_client import upsert_raw
    from ingest.pubsub_client import publish_raw_event
    from languages.models import Language

    if surveys_dir is None:
        surveys_dir = Path(__file__).resolve().parents[2] / 'data' / 'so_surveys'

    lang_id_map = {lang.name.lower(): lang.id for lang in Language.objects.all()}
    total = 0

    for year in range(2011, 2025):
        csv_path = surveys_dir / f'{year}.csv'
        if not csv_path.exists():
            logger.warning('SO CSV not found: %s — skipping year %d', csv_path, year)
            continue

        try:
            df = pd.read_csv(csv_path, low_memory=False)
        except Exception as exc:
            logger.error('could not read %s: %s', csv_path, exc)
            continue

        col = _detect_column(df, year)
        if col is None:
            logger.info('SO %d: no admired column found, skipping', year)
            continue
        if col not in df.columns:
            logger.warning('SO %d: column %r not in CSV, skipping', year, col)
            continue

        for lang in LANGUAGES:
            score = _score_for_language(df, col, lang)
            if score is None:
                continue
            for month in range(1, 13):
                upsert_raw(
                    source='so',
                    language=lang.lower(),
                    year=year,
                    month=month,
                    raw_value=score,
                    extra={'column_used': col},
                )
                publish_raw_event(
                    source='so',
                    language=lang.lower(),
                    year=year,
                    month=month,
                    raw_value=score,
                    language_id=lang_id_map.get(lang.lower()),
                )
                total += 1

        logger.info('SO %d: ingested %d rows', year, total)

    logger.info('SO ingest complete: %d total rows', total)
    return total


if __name__ == '__main__':
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fossil.settings.dev')
    django.setup()
    logging.basicConfig(level=logging.INFO)
    run()
