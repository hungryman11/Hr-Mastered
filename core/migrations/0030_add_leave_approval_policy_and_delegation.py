"""Add LeaveApprovalPolicy and ApprovalDelegation models."""
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_employee_org_admin_flag'),
    ]

    operations = [
        migrations.CreateModel(
            name='LeaveApprovalPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('first_approver_type', models.CharField(choices=[('HEAD', 'Unit Head'), ('ACTING', 'Acting Head'), ('MANAGER', 'Line Manager'), ('SPECIFIC', 'Specific Employee'), ('ROLE', 'Role-based')], default='HEAD', max_length=20)),
                ('final_approver_type', models.CharField(choices=[('HEAD', 'Unit Head'), ('ACTING', 'Acting Head'), ('MANAGER', 'Line Manager'), ('SPECIFIC', 'Specific Employee'), ('ROLE', 'Role-based')], default='ROLE', max_length=20)),
                ('policy', models.JSONField(default=dict, blank=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leaveapprovalpolicy_records', to='core.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='leaveapprovalpolicy_created_by', to='core.employee')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='leaveapprovalpolicy_updated_by', to='core.employee')),
                ('first_approver_employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='first_approver_policies', to='core.employee')),
                ('final_approver_employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='final_approver_policies', to='core.employee')),
                ('org_unit', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='leave_policy', to='core.orgunit')),
            ],
            options={'db_table': 'leave_approval_policies'},
        ),
        migrations.CreateModel(
            name='ApprovalDelegation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('active', models.BooleanField(default=True)),
                ('reason', models.TextField(blank=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approvaldelegation_records', to='core.company')),
                ('approver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='delegations_from', to='core.employee')),
                ('delegate_to', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='delegations_to', to='core.employee')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approvaldelegation_created_by', to='core.employee')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approvaldelegation_updated_by', to='core.employee')),
            ],
            options={'db_table': 'approval_delegations'},
        ),
    ]
