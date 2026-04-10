from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0009_creditapplication_status_fk'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicationstatushistory',
            name='metadata',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
