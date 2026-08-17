# Generated manually for the sequential leave-approval workflow.
import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0009_employee_zoho_user_id_leaverequest_document_name_and_more')]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='role',
            field=models.CharField(
                choices=[
                    ('ADMIN', 'Administrator'), ('SUPERVISOR', 'Supervisor'),
                    ('HOD', 'Head of Department'), ('HR_ADMIN', 'HR Admin'),
                    ('MANAGER', 'Manager'), ('EMPLOYEE', 'Employee'),
                ],
                default='EMPLOYEE', max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='LeaveApprovalStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('sequence', models.PositiveSmallIntegerField()),
                ('stage', models.CharField(choices=[('ADMIN', 'Administrator'), ('SUPERVISOR', 'Supervisor'), ('HOD', 'Head of Department'), ('HR', 'HR')], max_length=20)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='PENDING', max_length=20)),
                ('decision_reason', models.TextField(blank=True)),
                ('decided_at', models.DateTimeField(blank=True, null=True)),
                ('approver', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='assigned_leave_approval_steps', to='core.employee')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_records', to='core.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='leaveapprovalstep_created_by', to='core.employee')),
                ('leave_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approval_steps', to='core.leaverequest')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='leaveapprovalstep_updated_by', to='core.employee')),
            ],
            options={'db_table': 'leave_approval_steps', 'ordering': ('sequence', 'id')},
        ),
        migrations.AddConstraint(
            model_name='leaveapprovalstep',
            constraint=models.UniqueConstraint(fields=('leave_request', 'sequence', 'approver'), name='unique_leave_approval_step_approver'),
        ),
    ]
