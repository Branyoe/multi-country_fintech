from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Originally created the Country model in the 'applications' app.
    Now converted to remove Country from the applications state — the model
    lives in the 'countries' app. The actual DB table is untouched.
    """

    dependencies = [
        ('applications', '0002_applicationstatushistory_bankproviderdata_and_more'),
    ]

    operations = [
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
    ]
