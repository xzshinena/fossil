import datetime

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from languages.models import HealthScore, HistoricalEvent, Language


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def lang_c(db):
    return Language.objects.create(name='C', parent=None)


@pytest.fixture
def lang_cpp(db, lang_c):
    return Language.objects.create(name='C++', parent=lang_c)


@pytest.fixture
def lang_python(db, lang_c):
    return Language.objects.create(name='Python', parent=lang_c)


# ── /tree/ ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTreeView:
    def test_empty_db_returns_origins(self, client):
        resp = client.get('/tree/?year=2024&month=1')
        assert resp.status_code == 200
        data = resp.json()
        assert data['name'] == 'Origins'
        assert data['children'] == []

    def test_single_root_returned_directly(self, client, lang_c):
        resp = client.get('/tree/?year=2024&month=1')
        assert resp.status_code == 200
        data = resp.json()
        assert data['name'] == 'C'

    def test_multiple_roots_wrapped_in_origins(self, client, lang_c):
        Language.objects.create(name='Lisp', parent=None)
        resp = client.get('/tree/?year=2024&month=1')
        assert resp.status_code == 200
        data = resp.json()
        assert data['name'] == 'Origins'
        child_names = [c['name'] for c in data['children']]
        assert 'C' in child_names
        assert 'Lisp' in child_names

    def test_node_includes_id_field(self, client, lang_c):
        resp = client.get('/tree/?year=2024&month=1')
        data = resp.json()
        assert 'id' in data
        assert data['id'] == lang_c.id

    def test_health_score_none_when_no_score_row(self, client, lang_c):
        resp = client.get('/tree/?year=2024&month=1')
        data = resp.json()
        assert data['health_score'] is None
        assert data['partial'] is False

    def test_health_score_populated_from_db(self, client, lang_c):
        HealthScore.objects.create(
            language=lang_c, year=2024, month=1,
            score=75.5, partial=False,
            source_breakdown={'github': 80.0, 'so': 70.0},
        )
        resp = client.get('/tree/?year=2024&month=1')
        data = resp.json()
        assert data['health_score'] == 75.5
        assert data['source_breakdown'] == {'github': 80.0, 'so': 70.0}

    def test_partial_flag_propagated(self, client, lang_c):
        HealthScore.objects.create(
            language=lang_c, year=2024, month=1,
            score=60.0, partial=True, source_breakdown={},
        )
        resp = client.get('/tree/?year=2024&month=1')
        assert resp.json()['partial'] is True

    def test_children_sorted_alphabetically(self, client, lang_c, lang_cpp, lang_python):
        resp = client.get('/tree/?year=2024&month=1')
        data = resp.json()
        child_names = [c['name'] for c in data['children']]
        assert child_names == sorted(child_names)

    def test_score_scoped_to_requested_year_month(self, client, lang_c):
        HealthScore.objects.create(
            language=lang_c, year=2023, month=6,
            score=42.0, partial=False, source_breakdown={},
        )
        # Request a different period — score should NOT appear
        resp = client.get('/tree/?year=2024&month=1')
        assert resp.json()['health_score'] is None

    def test_default_year_month_accepted(self, client, lang_c):
        resp = client.get('/tree/')
        assert resp.status_code == 200

    def test_children_nested_correctly(self, client, lang_c, lang_cpp):
        resp = client.get('/tree/?year=2024&month=1')
        data = resp.json()
        assert data['name'] == 'C'
        assert len(data['children']) == 1
        assert data['children'][0]['name'] == 'C++'


# ── /events/ ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEventsEndpoint:
    def test_empty_returns_empty_list(self, client):
        resp = client.get('/events/')
        assert resp.status_code == 200
        assert resp.json() == []

    def test_events_returned_ordered_by_date(self, client, lang_c):
        HistoricalEvent.objects.create(
            date=datetime.date(2015, 5, 1),
            title='Rust 1.0',
            language=None,
            impact_description='First stable Rust release.',
        )
        HistoricalEvent.objects.create(
            date=datetime.date(2012, 3, 1),
            title='Go 1.0',
            language=lang_c,
            impact_description='First stable Go release.',
        )
        results = client.get('/events/').json()
        assert len(results) == 2
        assert results[0]['title'] == 'Go 1.0'
        assert results[1]['title'] == 'Rust 1.0'

    def test_event_includes_language_name(self, client, lang_c):
        HistoricalEvent.objects.create(
            date=datetime.date(2012, 3, 1),
            title='Go 1.0',
            language=lang_c,
            impact_description='Go stable.',
        )
        event = client.get('/events/').json()[0]
        assert event['language_name'] == 'C'

    def test_event_with_no_language(self, client):
        HistoricalEvent.objects.create(
            date=datetime.date(2022, 11, 1),
            title='ChatGPT launches',
            language=None,
            impact_description='LLM era begins.',
        )
        event = client.get('/events/').json()[0]
        assert event['language'] is None
        assert event['language_name'] is None


# ── /languages/ ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLanguagesEndpoint:
    def test_lists_all_languages(self, client, lang_c, lang_cpp):
        names = [l['name'] for l in client.get('/languages/').json()]
        assert 'C' in names
        assert 'C++' in names

    def test_parent_name_included(self, client, lang_cpp):
        langs = client.get('/languages/').json()
        cpp = next(l for l in langs if l['name'] == 'C++')
        assert cpp['parent_name'] == 'C'

    def test_root_language_has_null_parent(self, client, lang_c):
        langs = client.get('/languages/').json()
        c = next(l for l in langs if l['name'] == 'C')
        assert c['parent'] is None
        assert c['parent_name'] is None
