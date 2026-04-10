from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('countries', '0003_countrystatus_statustransition'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='statustransition',
            name='triggers_task',
        ),
    ]
