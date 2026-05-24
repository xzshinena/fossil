import logging
import os
import threading
from datetime import datetime

from django.conf import settings
from django.core.management import call_command
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Language, HealthScore, HistoricalEvent
from .serializers import LanguageSerializer, HealthScoreSerializer, HistoricalEventSerializer

logger = logging.getLogger(__name__)

_SCHEDULER_SA_EMAIL = os.environ.get('SCHEDULER_SA_EMAIL', '')


def _verify_oidc_token(request) -> bool:
    if settings.DEBUG:
        return True
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Bearer '):
        return False
    token = auth[len('Bearer '):]
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        claims = id_token.verify_oauth2_token(token, google_requests.Request())
        return (
            claims.get('email') == _SCHEDULER_SA_EMAIL
            and claims.get('email_verified', False)
        )
    except Exception:
        logger.exception('OIDC token verification failed')
        return False


def _run_ingest_background(source: str, incremental: bool) -> None:
    now = datetime.utcnow()
    try:
        if incremental:
            call_command('run_ingest', source=source, start_year=now.year, end_year=now.year)
        else:
            call_command('run_ingest', source='all', start_year=2011, end_year=now.year)
    except Exception:
        logger.exception('run_ingest failed (source=%s incremental=%s)', source, incremental)


@csrf_exempt
@require_POST
def ingest_run_view(request):
    if not _verify_oidc_token(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    source = request.GET.get('source', 'all')
    incremental = request.GET.get('incremental', 'false').lower() == 'true'

    thread = threading.Thread(
        target=_run_ingest_background,
        args=(source, incremental),
        daemon=True,
    )
    thread.start()

    return JsonResponse({'status': 'accepted', 'source': source, 'incremental': incremental}, status=202)


class LanguageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Language.objects.all().order_by('name')
    serializer_class = LanguageSerializer


class HealthScoreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HealthScore.objects.select_related('language').order_by(
        'language__name', 'year', 'month'
    )
    serializer_class = HealthScoreSerializer
    filterset_fields = ['language', 'year', 'month']


class HistoricalEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HistoricalEvent.objects.select_related('language').order_by('date')
    serializer_class = HistoricalEventSerializer


@api_view(['GET'])
def tree_view(request):
    year = int(request.query_params.get('year', 2024))
    month = int(request.query_params.get('month', 1))

    languages = {lang.id: lang for lang in Language.objects.all()}

    scores = {
        hs.language_id: hs
        for hs in HealthScore.objects.filter(year=year, month=month)
    }

    children_map = {lang_id: [] for lang_id in languages}
    roots = []
    for lang in languages.values():
        if lang.parent_id is None:
            roots.append(lang)
        else:
            children_map[lang.parent_id].append(lang)

    def build_node(lang):
        hs = scores.get(lang.id)
        return {
            'id': lang.id,
            'name': lang.name,
            'health_score': hs.score if hs else None,
            'partial': hs.partial if hs else False,
            'source_breakdown': hs.source_breakdown if hs else {},
            'children': [
                build_node(child)
                for child in sorted(children_map[lang.id], key=lambda lang: lang.name)
            ],
        }

    if len(roots) == 1:
        return Response(build_node(roots[0]))

    return Response({
        'name': 'Origins',
        'health_score': None,
        'partial': False,
        'source_breakdown': {},
        'children': [build_node(r) for r in sorted(roots, key=lambda lang: lang.name)],
    })
