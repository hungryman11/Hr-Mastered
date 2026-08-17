# Generated migration for LeaveBalance.year fix

from django.db import migrations, models
from django.utils import timezone


def set_current_year(apps, schema_editor):
    """Populate existing year=2026 records with current year."""
    LeaveBalance = apps.get_model('core', 'LeaveBalance')
    current_year = timezone.now().year
    # Update all 2026 balances to current year
    LeaveBalance.objects.filter(year=2026).update(year=current_year)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_alter_employee_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leavebalance',
            name='year',
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
        migrations.RunPython(set_current_year, migrations.RunPython.noop),
    ]
