"""
Pure composite health score computation + MySQL persistence.

Weights: GitHub 30%, SO 25%, Jobs (Adzuna) 25%, Citations (Scholar) 20%.
Missing sources have their weight redistributed proportionally.
If ALL sources are None for a month, score is None (no division by zero).
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

WEIGHTS: dict[str, float] = {
    'github': 0.30,
    'so': 0.25,
    'jobs': 0.25,
    'citations': 0.20,
}


def compute_health_score(
    github: Optional[float],
    so: Optional[float],
    jobs: Optional[float],
    citations: Optional[float],
) -> tuple[Optional[float], bool, dict]:
    """
    Returns (score, partial, source_breakdown).

    score   — 0-100 composite, or None if all sources missing.
    partial — True if any source is missing.
    source_breakdown — dict of available source values used.
    """
    sources = {'github': github, 'so': so, 'jobs': jobs, 'citations': citations}
    available = {k: v for k, v in sources.items() if v is not None}

    if not available:
        return None, True, {}

    partial = len(available) < len(WEIGHTS)
    total_weight = sum(WEIGHTS[k] for k in available)
    score = sum(v * WEIGHTS[k] / total_weight for k, v in available.items())

    return (
        round(max(0.0, min(100.0, score)), 2),
        partial,
        {k: round(v, 2) for k, v in available.items()},
    )


def normalize_series(values: list[float]) -> list[float]:
    """Min-max normalize a list to [0, 100]. Returns as-is if all values equal."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [50.0] * len(values)
    return [round((v - lo) / (hi - lo) * 100, 2) for v in values]


def persist_scores(year: int, month: int) -> int:
    """
    Read raw MongoDB values for all languages for the given year/month,
    normalize per-source, compute composite, write to MySQL HealthScore.
    Returns count of rows written.
    """
    from ingest.mongo_client import get_raw_collection
    from languages.models import Language, HealthScore

    col = get_raw_collection()
    lang_map = {lang.name.lower(): lang for lang in Language.objects.all()}

    def fetch_source(source: str) -> dict[str, float]:
        rows = col.find({'source': source, 'year': year, 'month': month})
        return {r['language'].lower(): r['raw_value'] for r in rows}

    raw = {
        'github': fetch_source('github'),
        'so': fetch_source('so'),
        'jobs': fetch_source('adzuna'),
        'citations': fetch_source('scholar'),
    }

    # Normalize each source across all languages for this month
    normalized: dict[str, dict[str, float]] = {}
    for source, lang_vals in raw.items():
        if not lang_vals:
            continue
        names = list(lang_vals.keys())
        norm_vals = normalize_series([lang_vals[n] for n in names])
        normalized[source] = dict(zip(names, norm_vals))

    written = 0
    for lang_name, lang_obj in lang_map.items():
        github = normalized.get('github', {}).get(lang_name)
        so = normalized.get('so', {}).get(lang_name)
        jobs = normalized.get('jobs', {}).get(lang_name)
        citations = normalized.get('citations', {}).get(lang_name)

        score, partial, breakdown = compute_health_score(github, so, jobs, citations)

        if score is None and not any([github, so, jobs, citations]):
            continue

        HealthScore.objects.update_or_create(
            language=lang_obj, year=year, month=month,
            defaults={
                'score': score,
                'partial': partial,
                'source_breakdown': breakdown,
            },
        )
        written += 1

    logger.info('persist_scores %d-%02d: wrote %d rows', year, month, written)
    return written
