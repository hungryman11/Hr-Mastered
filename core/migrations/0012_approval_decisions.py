# Auto-generated migration for ApprovalDecision model.
import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0011_leave_request_supporting_fields')]

    operations = [
        migrations.CreateModel(
            name='ApprovalDecision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('stage', models.CharField(blank=True, choices=[('ADMIN', 'Administrator'), ('SUPERVISOR', 'Supervisor'), ('HOD', 'Head of Department'), ('HR', 'HR')], max_length=20, null=True)),
                ('sequence', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('decision', models.CharField(choices=[('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('CANCELLATION', 'Cancellation')], max_length=20)),
                ('reason', models.TextField(blank=True)),
                ('decided_at', models.DateTimeField()),
                ('actor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='approval_decisions', to='core.employee')),
                ('approval_step', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='decisions', to='core.leaveapprovalstep')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_records', to='core.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approvaldecision_created_by', to='core.employee')),
                ('leave_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approval_decisions', to='core.leaverequest')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approvaldecision_updated_by', to='core.employee')),
            ],
            options={'db_table': 'approval_decisions', 'ordering': ('-decided_at', 'id')},
        ),
        migrations.AddConstraint(
            model_name='approvaldecision',
            constraint=models.UniqueConstraint(fields=('leave_request', 'approval_step', 'actor'), name='unique_decision_per_step_actor'),
        ),
    ]
