"""
Seed MySQL with language lineage and health scores.

Usage:
  python manage.py seed_so

SO survey CSVs (optional): place annual CSVs in data/so_surveys/<year>.csv
Download from: https://survey.stackoverflow.co/datasets

If no CSVs are found, synthetic trend data is generated so the tree
renders immediately without any downloads.
"""
import json
import os
import random
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand

from languages.models import Language, HealthScore

# Pre-2015 SO survey column mapping (from TODOS.md TODO-1)
SO_COLUMN_MAP = {
    2011: None,       # no direct "admired" equivalent
    2012: 'tech_use',
    2013: 'have_tech',
    2014: 'loved',
}

# Synthetic trend profiles: (start_score_2011, end_score_2024)
# Used as fallback when no SO CSVs are available.
SYNTHETIC_TRENDS = {
    'Python':     (42, 92),
    'JavaScript': (60, 78),
    'TypeScript': (0,  82),   # didn't exist until 2012
    'Java':       (68, 62),
    'C':          (52, 42),
    'C++':        (48, 50),
    'Go':         (0,  72),   # released 2012
    'Rust':       (0,  80),   # released 2015
    'Kotlin':     (0,  74),   # released 2016
    'Swift':      (0,  68),   # released 2014
    'Scala':      (38, 42),
    'Ruby':       (55, 38),
    'PHP':        (50, 36),
    'Perl':       (35, 18),
    'Haskell':    (28, 34),
    'R':          (25, 58),
    'Julia':      (0,  52),   # released 2012
    'Fortran':    (12, 10),
    'COBOL':      (10, 8),
    'Lisp':       (20, 22),
}

# Languages that didn't exist for part of the range (year they became relevant)
LANG_START_YEAR = {
    'TypeScript': 2012,
    'Go': 2012,
    'Rust': 2015,
    'Kotlin': 2016,
    'Swift': 2014,
    'Julia': 2013,
}


class Command(BaseCommand):
    help = 'Seed language lineage and health scores from SO survey CSVs (or synthetic data)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--synthetic-only',
            action='store_true',
            help='Skip CSV parsing and use synthetic trend data',
        )

    def handle(self, *args, **options):
        data_dir = Path(__file__).resolve().parents[6] / 'data'
        lineage_path = data_dir / 'lineage.json'
        surveys_dir = data_dir / 'so_surveys'

        self._load_lineage(lineage_path)

        if options['synthetic_only']:
            self._seed_synthetic()
            return

        csv_files = sorted(surveys_dir.glob('*.csv')) if surveys_dir.exists() else []

        if csv_files:
            self.stdout.write(f'Found {len(csv_files)} SO survey CSV(s)')
            seeded = 0
            for csv_path in csv_files:
                seeded += self._seed_from_csv(csv_path)
            self.stdout.write(self.style.SUCCESS(f'Seeded {seeded} health score rows from SO CSVs'))
        else:
            self.stdout.write('No SO survey CSVs found — generating synthetic trend data')
            self._seed_synthetic()

    def _load_lineage(self, lineage_path: Path):
        with open(lineage_path) as f:
            entries = json.load(f)

        # Two passes: create all languages, then wire parents.
        lang_map = {}
        for entry in entries:
            lang, _ = Language.objects.update_or_create(
                name=entry['name'],
                defaults={'parent': None},
            )
            lang_map[entry['name']] = lang

        for entry in entries:
            if entry['parent']:
                lang = lang_map[entry['name']]
                lang.parent = lang_map[entry['parent']]
                lang.save(update_fields=['parent'])

        self.stdout.write(self.style.SUCCESS(f'Loaded {len(lang_map)} languages from lineage.json'))

    def _seed_from_csv(self, csv_path: Path) -> int:
        try:
            year = int(csv_path.stem)
        except ValueError:
            self.stdout.write(self.style.WARNING(f'Skipping {csv_path.name} (expected YYYY.csv)'))
            return 0

        try:
            df = pd.read_csv(csv_path, low_memory=False)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not read {csv_path.name}: {e}'))
            return 0

        col = SO_COLUMN_MAP.get(year, self._detect_admired_column(df, year))
        if col is None or col not in df.columns:
            self.stdout.write(self.style.WARNING(f'{year}: admired column not found, skipping'))
            return 0

        seeded = 0
        for lang in Language.objects.all():
            score = self._extract_score(df, col, lang.name, year)
            if score is None:
                continue
            for month in range(1, 13):
                HealthScore.objects.update_or_create(
                    language=lang, year=year, month=month,
                    defaults={
                        'score': round(score, 2),
                        'partial': True,
                        'source_breakdown': {'so': round(score, 2)},
                    },
                )
                seeded += 1

        return seeded

    def _detect_admired_column(self, df: pd.DataFrame, year: int) -> str | None:
        candidates = [
            'LanguageWorkedWith', 'HaveWorkedLanguage',
            'AdmiredLanguage', 'LanguageWantToWorkWith',
        ]
        for c in candidates:
            if c in df.columns:
                return c
        return None

    def _extract_score(self, df: pd.DataFrame, col: str, lang_name: str, year: int):
        """Return a 0-100 admiration score for lang_name from the given column."""
        try:
            hits = df[col].dropna().astype(str)
            total = len(hits)
            if total == 0:
                return None
            matches = hits.str.contains(lang_name, case=False, regex=False).sum()
            return (matches / total) * 100
        except Exception:
            return None

    def _seed_synthetic(self):
        """Generate deterministic trend-based health scores for 2011-2024."""
        rng = random.Random(42)
        seeded = 0

        for lang in Language.objects.all():
            trend = SYNTHETIC_TRENDS.get(lang.name)
            if trend is None:
                trend = (20, 20)

            start_score, end_score = trend
            start_year = LANG_START_YEAR.get(lang.name, 2011)
            total_months = (2024 - 2011) * 12 + 12

            for year in range(2011, 2025):
                for month in range(1, 13):
                    if year < start_year:
                        continue

                    month_index = (year - 2011) * 12 + (month - 1)
                    lang_start_index = (start_year - 2011) * 12
                    progress = (month_index - lang_start_index) / max(total_months - lang_start_index, 1)

                    base = start_score + (end_score - start_score) * progress
                    noise = rng.gauss(0, 2.5)
                    score = max(0.0, min(100.0, base + noise))

                    HealthScore.objects.update_or_create(
                        language=lang, year=year, month=month,
                        defaults={
                            'score': round(score, 2),
                            'partial': True,
                            'source_breakdown': {'so_synthetic': round(score, 2)},
                        },
                    )
                    seeded += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded {seeded} synthetic health score rows'))
