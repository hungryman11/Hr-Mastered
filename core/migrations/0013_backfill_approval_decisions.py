from django.db import migrations


def forwards(apps, schema_editor):
    from django.utils import timezone
    from django.db import IntegrityError

    LeaveApprovalStep = apps.get_model('core', 'LeaveApprovalStep')
    ApprovalDecision = apps.get_model('core', 'ApprovalDecision')
    LeaveRequest = apps.get_model('core', 'LeaveRequest')
    Employee = apps.get_model('core', 'Employee')

    # Backfill from LeaveApprovalStep entries that have been decided
    steps = LeaveApprovalStep.objects.filter(status__in=['APPROVED', 'REJECTED']).select_related('updated_by', 'approver', 'leave_request', 'company')
    for step in steps.iterator():
        actor = step.updated_by or step.approver
        if not actor:
            # Skip steps with no actor information
            continue
        decided_at = step.decided_at or getattr(step, 'updated_at', None) or timezone.now()
        decision_value = 'APPROVED' if step.status == 'APPROVED' else 'REJECTED'
        try:
            ApprovalDecision.objects.create(
                company=step.company,
                leave_request=step.leave_request,
                approval_step=step,
                actor=actor,
                stage=step.stage,
                sequence=step.sequence,
                decision=decision_value,
                reason=(step.decision_reason or ''),
                decided_at=decided_at,
                created_by=actor,
                updated_by=actor,
            )
        except IntegrityError:
            # Skip duplicates (migration may be re-run in dev)
            continue

    # Backfill from LeaveRequest-level reviewed fields where no decision exists
    requests = LeaveRequest.objects.filter(status__in=['APPROVED', 'REJECTED']).select_related('reviewed_by', 'company')
    for lr in requests.iterator():
        # If there are already ApprovalDecision rows for this leave request, skip
        if ApprovalDecision.objects.filter(leave_request=lr).exists():
            continue
        actor = lr.reviewed_by
        if not actor:
            continue
        decided_at = getattr(lr, 'reviewed_at', None) or timezone.now()
        decision_value = 'APPROVED' if lr.status == 'APPROVED' else 'REJECTED'
        reason = lr.rejection_reason or ''
        try:
            ApprovalDecision.objects.create(
                company=lr.company,
                leave_request=lr,
                approval_step=None,
                actor=actor,
                stage=None,
                sequence=None,
                decision=decision_value,
                reason=reason,
                decided_at=decided_at,
                created_by=actor,
                updated_by=actor,
            )
        except IntegrityError:
            continue


def reverse(apps, schema_editor):
    # No-op reverse: do not remove decisions automatically
    return


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_approval_decisions'),
    ]

    operations = [
        migrations.RunPython(forwards, reverse),
    ]
