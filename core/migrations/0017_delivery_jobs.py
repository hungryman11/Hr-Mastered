import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0016_protect_approval_decisions')]

    operations = [
        migrations.CreateModel(
            name='DeliveryJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('kind', models.CharField(choices=[('EMAIL', 'Email'), ('APPROVAL_DOCUMENT', 'Approval document upload')], max_length=30)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('SUCCEEDED', 'Succeeded'), ('FAILED', 'Failed')], default='PENDING', max_length=20)),
                ('payload', models.JSONField()),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('last_error', models.TextField(blank=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_records', to='core.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deliveryjob_created_by', to='core.employee')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deliveryjob_updated_by', to='core.employee')),
            ],
            options={'db_table': 'delivery_jobs'},
        ),
        migrations.AddIndex(model_name='deliveryjob', index=models.Index(fields=['status', 'created_at'], name='delivery_jo_status_1a2c8c_idx')),
    ]
