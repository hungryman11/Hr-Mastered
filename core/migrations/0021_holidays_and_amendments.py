import django.db.models.deletion
import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0020_delivery_job_leases')]

    operations = [
        migrations.CreateModel(
            name='CompanyHoliday',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('name', models.CharField(max_length=150)),
                ('date', models.DateField()),
                ('is_national', models.BooleanField(default=False)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_records', to='core.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='companyholiday_created_by', to='core.employee')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='companyholiday_updated_by', to='core.employee')),
            ],
            options={'db_table': 'company_holidays', 'ordering': ('date',)},
        ),
        migrations.AddConstraint(model_name='companyholiday', constraint=models.UniqueConstraint(fields=('company', 'date'), name='unique_company_holiday_date')),
        migrations.AddField(model_name='leaverequest', name='amendment_reason', field=models.TextField(blank=True)),
        migrations.AddField(model_name='leaverequest', name='amendment_requested_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='leaverequest', name='amendment_requested_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='requested_leave_amendments', to='core.employee')),
        migrations.AddField(model_name='leaverequest', name='approval_round', field=models.PositiveSmallIntegerField(default=1)),
        migrations.AddField(model_name='leaveapprovalstep', name='approval_round', field=models.PositiveSmallIntegerField(default=1)),
        migrations.AlterField(model_name='leaverequest', name='status', field=models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('CANCELLED', 'Cancelled'), ('AMENDMENT_REQUESTED', 'Amendment requested')], default='PENDING', max_length=20)),
        migrations.AlterField(model_name='leaveapprovalstep', name='status', field=models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('AMENDMENT_REQUESTED', 'Amendment requested')], default='PENDING', max_length=20)),
        migrations.AlterField(model_name='approvaldecision', name='decision', field=models.CharField(choices=[('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('CANCELLATION', 'Cancellation'), ('AMENDMENT_REQUESTED', 'Amendment requested')], max_length=20)),
        migrations.RemoveConstraint(model_name='leaveapprovalstep', name='unique_leave_approval_step_approver'),
        migrations.AddConstraint(model_name='leaveapprovalstep', constraint=models.UniqueConstraint(fields=('leave_request', 'approval_round', 'sequence', 'approver'), name='unique_leave_approval_step_approver')),
    ]
