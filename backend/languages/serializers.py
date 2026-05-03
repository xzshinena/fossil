from rest_framework import serializers
from .models import Language, HealthScore, HistoricalEvent


class LanguageSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True, default=None)

    class Meta:
        model = Language
        fields = ['id', 'name', 'parent', 'parent_name']


class HealthScoreSerializer(serializers.ModelSerializer):
    language_name = serializers.CharField(source='language.name', read_only=True)

    class Meta:
        model = HealthScore
        fields = [
            'id', 'language', 'language_name',
            'year', 'month', 'score', 'partial', 'source_breakdown',
        ]


class HistoricalEventSerializer(serializers.ModelSerializer):
    language_name = serializers.CharField(source='language.name', read_only=True, default=None)

    class Meta:
        model = HistoricalEvent
        fields = ['id', 'date', 'title', 'language', 'language_name', 'impact_description']
