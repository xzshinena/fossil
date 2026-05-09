import re
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from languages.models import HealthScore, Language


def _run_export(project='fossil-dev'):
    """Call export_to_bq with a mocked BigQuery client; return captured rows."""
    captured = []
    mock_job = MagicMock()
    mock_job.destination.project = project
    mock_job.destination.dataset_id = 'fossil'
    mock_job.destination.table_id = 'health_scores'

    mock_client = MagicMock()
    mock_client.load_table_from_json.side_effect = (
        lambda rows, *a, **kw: captured.extend(rows) or mock_job
    )

    with patch('google.cloud.bigquery', create=True) as mock_bq:
        mock_bq.Client.return_value = mock_client
        mock_bq.SchemaField.from_api_repr.side_effect = lambda col: col
        mock_bq.Table.return_value = MagicMock()
        mock_bq.LoadJobConfig.return_value = MagicMock()
        mock_bq.WriteDisposition.WRITE_TRUNCATE = 'WRITE_TRUNCATE'
        mock_bq.SourceFormat.NEWLINE_DELIMITED_JSON = 'NEWLINE_DELIMITED_JSON'

        call_command('export_to_bq', project=project, stdout=StringIO())

    return captured


@pytest.fixture
def lang(db):
    return Language.objects.create(name='Python', parent=None)


# ── row count ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_row_count_matches_queryset(lang):
    HealthScore.objects.create(
        language=lang, year=2023, month=1, score=80.0, partial=False,
        source_breakdown={'github': 80.0, 'so': 70.0, 'jobs': 60.0, 'citations': 50.0},
    )
    HealthScore.objects.create(
        language=lang, year=2023, month=2, score=75.0, partial=False,
        source_breakdown={'github': 75.0},
    )
    rows = _run_export()
    assert len(rows) == HealthScore.objects.count()


# ── so_score None for synthetic rows ─────────────────────────────────────────

@pytest.mark.django_db
def test_so_score_none_for_synthetic_breakdown(lang):
    # seed_so writes 'so_synthetic', not 'so' — so_score must be None
    HealthScore.objects.create(
        language=lang, year=2023, month=1, score=60.0, partial=True,
        source_breakdown={'so_synthetic': 42.5, 'github': 70.0},
    )
    rows = _run_export()
    assert rows[0]['so_score'] is None


@pytest.mark.django_db
def test_so_score_populated_for_real_so_key(lang):
    HealthScore.objects.create(
        language=lang, year=2023, month=1, score=70.0, partial=False,
        source_breakdown={'so': 55.0, 'github': 80.0},
    )
    rows = _run_export()
    assert rows[0]['so_score'] == 55.0


# ── language_name populated ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_language_name_populated(lang):
    HealthScore.objects.create(
        language=lang, year=2023, month=1, score=50.0, partial=False,
        source_breakdown={},
    )
    rows = _run_export()
    assert rows[0]['language_name'] == 'Python'


@pytest.mark.django_db
def test_language_name_populated_for_all_rows(db):
    lang_a = Language.objects.create(name='Rust', parent=None)
    lang_b = Language.objects.create(name='Go', parent=None)
    for lang in (lang_a, lang_b):
        HealthScore.objects.create(
            language=lang, year=2023, month=1, score=50.0, partial=False,
            source_breakdown={},
        )
    rows = _run_export()
    assert all(row['language_name'] for row in rows)


# ── ingested_at is ISO 8601 string ───────────────────────────────────────────

ISO_8601_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')

@pytest.mark.django_db
def test_ingested_at_is_iso8601_string(lang):
    HealthScore.objects.create(
        language=lang, year=2023, month=1, score=50.0, partial=False,
        source_breakdown={},
    )
    rows = _run_export()
    value = rows[0]['ingested_at']
    assert isinstance(value, str), f'ingested_at must be str, got {type(value)}'
    assert ISO_8601_RE.match(value), f'ingested_at not ISO 8601: {value!r}'


# ── empty queryset ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_empty_queryset_loads_zero_rows(db):
    rows = _run_export()
    assert rows == []
