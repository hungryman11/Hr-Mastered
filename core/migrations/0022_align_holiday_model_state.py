import django.db.models.deletion

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0021_holidays_and_amendments')]

    operations = [
        migrations.AlterField(
            model_name='approvaldecision', name='decision',
            field=models.CharField(choices=[('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('CANCELLATION', 'Cancellation'), ('AMENDMENT_REQUESTED', 'Amendment requested')], max_length=20),
        ),
        migrations.AlterField(
            model_name='companyholiday', name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='companyholiday', name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL),
        ),
    ]
