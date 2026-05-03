from django.db import models


class Language(models.Model):
    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='children',
    )

    class Meta:
        db_table = 'languages'

    def __str__(self):
        return self.name


class HealthScore(models.Model):
    language = models.ForeignKey(
        Language, on_delete=models.CASCADE,
        related_name='health_scores',
    )
    year = models.IntegerField()
    month = models.IntegerField()
    score = models.FloatField(null=True, blank=True)
    partial = models.BooleanField(default=False)
    source_breakdown = models.JSONField(default=dict)

    class Meta:
        db_table = 'health_scores'
        unique_together = [('language', 'year', 'month')]
        indexes = [
            models.Index(fields=['language', 'year', 'month']),
        ]

    def __str__(self):
        return f'{self.language.name} {self.year}/{self.month:02d}: {self.score}'
