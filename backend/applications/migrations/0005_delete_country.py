from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('applications', '0004_remove_countryvalidation'),
        ('countries', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='Country'),
            ],
        ),
    ]