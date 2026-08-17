import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0017_delivery_jobs')]

    operations = [
        migrations.RenameIndex(
            model_name='deliveryjob', old_name='delivery_jo_status_1a2c8c_idx',
            new_name='delivery_jo_status_388a6f_idx',
        ),
        migrations.AlterField(
            model_name='deliveryjob', name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='deliveryjob', name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL),
        ),
    ]
