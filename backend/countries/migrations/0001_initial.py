from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Registers the Country model in the 'countries' app state
    without touching the actual DB table (already created by applications/0003_country).
    """

    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],  # table already exists — do not touch it
            state_operations=[
                migrations.CreateModel(
                    name='Country',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('code', models.CharField(max_length=10, unique=True)),
                        ('label', models.CharField(max_length=100)),
                        ('document_type', models.CharField(max_length=50)),
                        ('document_hint', models.CharField(max_length=200)),
                        ('document_example', models.CharField(max_length=100)),
                        ('document_regex', models.CharField(max_length=500)),
                        ('is_active', models.BooleanField(default=True)),
                    ],
                    options={
                        'db_table': 'country',
                        'ordering': ['code'],
                    },
                ),
            ],
        ),
    ]
