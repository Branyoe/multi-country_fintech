"""
Migrates CreditApplication.status from CharField to FK → CountryStatus.

Steps:
1. Add nullable status_new FK
2. Backfill from existing status string values
3. Remove old status CharField
4. Rename status_new → status
"""
import django.db.models.deletion
from django.db import migrations, models


def backfill_status_fk(apps, schema_editor):
    CreditApplication = apps.get_model('applications', 'CreditApplication')
    CountryStatus = apps.get_model('countries', 'CountryStatus')

    for app in CreditApplication.objects.select_related('country_ref').iterator():
        if app.country_ref_id is None or not app.status_old:
            continue
        cs = CountryStatus.objects.filter(
            country_id=app.country_ref_id,
            code=app.status_old,
        ).first()
        if cs is not None:
            CreditApplication.objects.filter(id=app.id).update(status_new=cs)


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0008_remove_creditapplication_country'),
        ('countries', '0003_countrystatus_statustransition'),
    ]

    operations = [
        # 1. Rename existing status CharField → status_old (keep data)
        migrations.RenameField(
            model_name='creditapplication',
            old_name='status',
            new_name='status_old',
        ),
        # 2. Add new status FK, nullable for the backfill
        migrations.AddField(
            model_name='creditapplication',
            name='status_new',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='+',
                to='countries.countrystatus',
            ),
        ),
        # 3. Backfill status_new from status_old + country_ref
        migrations.RunPython(backfill_status_fk, migrations.RunPython.noop),
        # 4. Drop old CharField
        migrations.RemoveField(model_name='creditapplication', name='status_old'),
        # 5. Rename status_new → status
        migrations.RenameField(
            model_name='creditapplication',
            old_name='status_new',
            new_name='status',
        ),
    ]
