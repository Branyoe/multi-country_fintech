import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('countries', '0002_countryvalidation'),
    ]

    operations = [
        migrations.CreateModel(
            name='CountryStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50)),
                ('label', models.CharField(max_length=100)),
                ('is_initial', models.BooleanField(default=False, help_text='Estado inicial al crear la solicitud')),
                ('is_terminal', models.BooleanField(default=False, help_text='No acepta más transiciones')),
                ('order', models.IntegerField(default=0, help_text='Orden de presentación en UI')),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='statuses', to='countries.country')),
            ],
            options={
                'db_table': 'country_status',
                'ordering': ['country', 'order'],
            },
        ),
        migrations.AddConstraint(
            model_name='countrystatus',
            constraint=models.UniqueConstraint(fields=['country', 'code'], name='unique_country_status_code'),
        ),
        migrations.CreateModel(
            name='StatusTransition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('triggers_task', models.CharField(blank=True, help_text='Nombre del task Celery a disparar al entrar al estado destino', max_length=100)),
                ('from_status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outgoing_transitions', to='countries.countrystatus')),
                ('to_status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='incoming_transitions', to='countries.countrystatus')),
            ],
            options={
                'db_table': 'status_transition',
            },
        ),
        migrations.AddConstraint(
            model_name='statustransition',
            constraint=models.UniqueConstraint(fields=['from_status', 'to_status'], name='unique_status_transition'),
        ),
    ]
