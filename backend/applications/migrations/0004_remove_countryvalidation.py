from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('applications', '0003_country'),
        ('countries', '0002_countryvalidation'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='CountryValidation'),
            ],
        ),
    ]