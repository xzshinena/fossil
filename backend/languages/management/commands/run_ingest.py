"""
Orchestrate the full Week 2 data pipeline.

Runs all 5 ingest scripts sequentially, then normalises raw MongoDB values
and writes composite HealthScore rows to MySQL.

Usage:
  python manage.py run_ingest                     # full run 2011-2024
  python manage.py run_ingest --source github     # single source
  python manage.py run_ingest --year 2023         # single year (score only)
  python manage.py run_ingest --skip-scores       # ingest without score computation
"""
import logging
from datetime import datetime

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

SOURCES = ['github', 'so', 'tiobe', 'scholar', 'adzuna']


class Command(BaseCommand):
    help = 'Run the full data ingestion pipeline and recompute health scores'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            choices=SOURCES + ['all'],
            default='all',
            help='Which ingest source to run (default: all)',
        )
        parser.add_argument(
            '--year',
            type=int,
            default=None,
            help='Limit score recomputation to a single year',
        )
        parser.add_argument(
            '--start-year',
            type=int,
            default=2011,
            help='First year for ingest scripts (default: 2011)',
        )
        parser.add_argument(
            '--end-year',
            type=int,
            default=2024,
            help='Last year for ingest scripts (default: 2024)',
        )
        parser.add_argument(
            '--skip-scores',
            action='store_true',
            help='Run ingest scripts but skip health score computation',
        )

    def handle(self, *args, **options):
        source = options['source']
        start_year = options['start_year']
        end_year = options['end_year']
        skip_scores = options['skip_scores']
        single_year = options['year']

        t0 = datetime.now()

        # --- Ingest phase ---
        if source in ('all', 'github'):
            self._run('github', start_year, end_year)

        if source in ('all', 'so'):
            self._run('so', start_year, end_year)

        if source in ('all', 'tiobe'):
            self._run('tiobe', start_year, end_year)

        if source in ('all', 'scholar'):
            self._run('scholar', start_year, end_year)

        if source in ('all', 'adzuna'):
            self._run('adzuna', start_year, end_year)

        # --- Score computation phase ---
        if not skip_scores:
            years = [single_year] if single_year else list(range(start_year, end_year + 1))
            self._compute_scores(years)

        elapsed = (datetime.now() - t0).total_seconds()
        self.stdout.write(self.style.SUCCESS(f'Pipeline complete in {elapsed:.1f}s'))

    def _run(self, source: str, start_year: int, end_year: int) -> None:
        self.stdout.write(f'  [{source}] ingesting {start_year}–{end_year}...')
        try:
            if source == 'github':
                from ingest.ingest_github import run
                count = run(start_year, end_year)
            elif source == 'so':
                from ingest.ingest_so import run
                count = run()
            elif source == 'tiobe':
                from ingest.ingest_tiobe import run
                count = run()
            elif source == 'scholar':
                from ingest.ingest_scholar import run
                count = run(start_year, end_year)
            elif source == 'adzuna':
                from ingest.ingest_adzuna import run
                count = run(start_year, end_year)
            else:
                return
            self.stdout.write(self.style.SUCCESS(f'  [{source}] {count} rows written'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'  [{source}] failed: {exc}'))
            logger.exception('ingest source %s failed', source)

    def _compute_scores(self, years: list[int]) -> None:
        from ingest.compute_health_score import persist_scores

        self.stdout.write('  [scores] computing composite health scores...')
        total = 0
        for year in years:
            for month in range(1, 13):
                try:
                    written = persist_scores(year, month)
                    total += written
                except Exception as exc:
                    logger.error('persist_scores %d-%02d failed: %s', year, month, exc)

        self.stdout.write(self.style.SUCCESS(f'  [scores] {total} HealthScore rows written'))
