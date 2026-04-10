import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('countries', '0001_initial'),
        ('applications', '0003_country'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='CountryValidation',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('rule_name', models.CharField(max_length=100)),
                        ('passed', models.BooleanField()),
                        ('detail', models.CharField(blank=True, max_length=255)),
                        ('evaluated_at', models.DateTimeField(auto_now_add=True)),
                        (
                            'application',
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name='validations',
                                to='applications.creditapplication',
                            ),
                        ),
                    ],
                    options={
                        'db_table': 'country_validations',
                        'verbose_name_plural': 'Country Validations',
                    },
                ),
            ],
        ),
    ]