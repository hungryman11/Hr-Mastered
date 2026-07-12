from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_employee_org_unit'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApprovalDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('document_type', models.CharField(choices=[('APPROVAL', 'Approval'), ('REJECTION', 'Rejection'), ('CANCELLATION', 'Cancellation')], max_length=20)),
                ('file_name', models.CharField(max_length=255)),
                ('file_path', models.CharField(max_length=500)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_records', to='core.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_approval_documents', to='core.employee')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to='core.employee')),
                ('leave_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approval_documents', to='core.leaverequest')),
            ],
            options={
                'db_table': 'approval_documents',
            },
        ),
    ]
