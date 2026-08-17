from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [('core', '0019_approval_document_delivery_state')]

    operations = [
        migrations.AddField(
            model_name='deliveryjob',
            name='available_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='deliveryjob',
            name='locked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='deliveryjob',
            index=models.Index(fields=['status', 'available_at'], name='delivery_status_available_idx'),
        ),
    ]
