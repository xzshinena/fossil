from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('parent', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='children',
                    to='languages.language',
                )),
            ],
            options={'db_table': 'languages'},
        ),
        migrations.CreateModel(
            name='HealthScore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.IntegerField()),
                ('month', models.IntegerField()),
                ('score', models.FloatField(blank=True, null=True)),
                ('partial', models.BooleanField(default=False)),
                ('source_breakdown', models.JSONField(default=dict)),
                ('language', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='health_scores',
                    to='languages.language',
                )),
            ],
            options={'db_table': 'health_scores'},
        ),
        migrations.AlterUniqueTogether(
            name='healthscore',
            unique_together={('language', 'year', 'month')},
        ),
        migrations.AddIndex(
            model_name='healthscore',
            index=models.Index(fields=['language', 'year', 'month'], name='health_scor_languag_idx'),
        ),
    ]
