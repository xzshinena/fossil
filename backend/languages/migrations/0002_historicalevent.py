from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('languages', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('title', models.CharField(max_length=200)),
                ('language', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='events',
                    to='languages.language',
                )),
                ('impact_description', models.TextField()),
            ],
            options={
                'db_table': 'historical_events',
                'ordering': ['date'],
            },
        ),
    ]
