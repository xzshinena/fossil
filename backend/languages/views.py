from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Language, HealthScore
from .serializers import LanguageSerializer, HealthScoreSerializer


class LanguageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Language.objects.all().order_by('name')
    serializer_class = LanguageSerializer


class HealthScoreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HealthScore.objects.select_related('language').order_by(
        'language__name', 'year', 'month'
    )
    serializer_class = HealthScoreSerializer
    filterset_fields = ['language', 'year', 'month']


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
