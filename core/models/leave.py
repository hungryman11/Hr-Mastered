from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .base import CompanyScopedModel


class LeaveType(CompanyScopedModel):
    class ProrationRule(models.TextChoices):
        NONE = 'NONE', 'No proration'
        LINEAR = 'LINEAR', 'Linear monthly proration'

    name = models.CharField(max_length=100)
    default_days = models.DecimalField(max_digits=5, decimal_places=1)
    requires_supporting_document = models.BooleanField(
        default=False,
        help_text='When enabled, employees must upload a supporting document (e.g. a medical note) with the request.',
    )
    max_days_per_request = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        help_text='Maximum days per single leave request. If null, global system default applies.',
    )
    carry_over_days = models.DecimalField(
        max_digits=5, decimal_places=1, default=0,
        help_text='Maximum unused days that can be carried over to the next calendar year.',
    )
    proration_rule = models.CharField(
        max_length=20, choices=ProrationRule.choices, default=ProrationRule.NONE,
    )

    class Meta:
        db_table = 'leave_types'

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class LeaveBalance(CompanyScopedModel):
    employee = models.ForeignKey(
        'core.Employee',
        on_delete=models.CASCADE,
        related_name='leave_balances',
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='balances',
    )
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    allocated_days = models.DecimalField(max_digits=5, decimal_places=1)
    carried_over_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        db_table = 'leave_balances'
        unique_together = ('employee', 'leave_type', 'year')

    def save(self, *args, **kwargs):
        """Automatically set year to current year if not provided."""
        if self.year is None:
            self.year = timezone.now().year
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.username} - {self.leave_type.name} ({self.year})"

    @property
    def remaining_days(self):
        return (self.allocated_days + self.carried_over_days) - self.used_days


class LeaveRequest(CompanyScopedModel):
    class Status(models.TextChoices):
        # Two-stage approval statuses (current)
        PENDING_DEPARTMENT_HEAD = 'PENDING_DEPARTMENT_HEAD', 'Pending Department Head Approval'
        PENDING_HR = 'PENDING_HR', 'Pending HR Approval'
        # Terminal and intermediate statuses
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'
        AMENDMENT_REQUESTED = 'AMENDMENT_REQUESTED', 'Amendment requested'
        # Legacy alias kept for backward compatibility with amendment round resets
        PENDING = 'PENDING', 'Pending (legacy)'

    employee = models.ForeignKey(
        'core.Employee',
        on_delete=models.CASCADE,
        related_name='leave_requests',
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='requests',
    )
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.TextField(blank=True)
    contact_during_leave = models.CharField(max_length=255)
    emergency_contact_name = models.CharField(max_length=255)
    emergency_contact_phone = models.CharField(max_length=50)
    handover_contact = models.CharField(max_length=255)
    handover_notes = models.TextField()
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_DEPARTMENT_HEAD,
    )
    reviewed_by = models.ForeignKey(
        'core.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_leave_requests',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    amendment_reason = models.TextField(blank=True)
    amendment_requested_by = models.ForeignKey(
        'core.Employee', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='requested_leave_amendments',
    )
    amendment_requested_at = models.DateTimeField(null=True, blank=True)
    approval_round = models.PositiveSmallIntegerField(default=1)
    document_name = models.CharField(max_length=255, blank=True, null=True)
    zoho_file_id = models.CharField(max_length=150, blank=True, null=True)
    workdrive_url = models.URLField(max_length=500, blank=True, null=True)
    supporting_document_name = models.CharField(max_length=255, blank=True, null=True)
    supporting_zoho_file_id = models.CharField(max_length=150, blank=True, null=True)
    supporting_workdrive_url = models.URLField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'leave_requests'

    def __str__(self):
        return f"{self.employee.username} - {self.leave_type.name} ({self.status})"


class ApprovalDocument(CompanyScopedModel):
    class DocumentType(models.TextChoices):
        APPROVAL = 'APPROVAL', 'Approval'
        REJECTION = 'REJECTION', 'Rejection'
        CANCELLATION = 'CANCELLATION', 'Cancellation'

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name='approval_documents',
    )
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    zoho_file_id = models.CharField(max_length=150, blank=True, null=True)
    upload_status = models.CharField(max_length=20, default='PENDING')
    upload_error = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'core.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_approval_documents',
    )

    class Meta:
        db_table = 'approval_documents'

    def __str__(self):
        return f"{self.document_type} - {self.file_name}"


class LeaveApprovalStep(CompanyScopedModel):
    """An immutable snapshot of one stage in a leave request's approval route."""

    class Stage(models.TextChoices):
        DEPT_HEAD = 'DEPT_HEAD', 'Department Head'
        HR = 'HR', 'HR'
        # Legacy stage values retained for existing DB rows
        ADMIN = 'ADMIN', 'Administrator'
        SUPERVISOR = 'SUPERVISOR', 'Supervisor'
        HOD = 'HOD', 'Head of Department'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        AMENDMENT_REQUESTED = 'AMENDMENT_REQUESTED', 'Amendment requested'

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name='approval_steps',
    )
    sequence = models.PositiveSmallIntegerField()
    approval_round = models.PositiveSmallIntegerField(default=1)
    stage = models.CharField(max_length=20, choices=Stage.choices)
    approver = models.ForeignKey(
        'core.Employee',
        on_delete=models.PROTECT,
        related_name='assigned_leave_approval_steps',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    decision_reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'leave_approval_steps'
        ordering = ('sequence', 'id')
        constraints = [
            models.UniqueConstraint(
                fields=('leave_request', 'approval_round', 'sequence', 'approver'),
                name='unique_leave_approval_step_approver',
            ),
        ]

    def __str__(self):
        return f"{self.leave_request_id}: {self.stage} / {self.approver_id} ({self.status})"


class ApprovalDecision(CompanyScopedModel):
    """Immutable record of an approval action taken on a leave request.

    Stores actor, decision, reason and timestamp. Kept immutable once created.
    """

    class Decision(models.TextChoices):
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLATION = 'CANCELLATION', 'Cancellation'
        AMENDMENT_REQUESTED = 'AMENDMENT_REQUESTED', 'Amendment requested'

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name='approval_decisions',
    )
    approval_step = models.ForeignKey(
        LeaveApprovalStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='decisions',
    )
    actor = models.ForeignKey(
        'core.Employee',
        on_delete=models.PROTECT,
        related_name='approval_decisions',
    )
    stage = models.CharField(max_length=20, choices=LeaveApprovalStep.Stage.choices, null=True, blank=True)
    sequence = models.PositiveSmallIntegerField(null=True, blank=True)
    decision = models.CharField(max_length=20, choices=Decision.choices)
    reason = models.TextField(blank=True)
    decided_at = models.DateTimeField()

    class Meta:
        db_table = 'approval_decisions'
        ordering = ('-decided_at', 'id')
        constraints = [
            models.UniqueConstraint(
                fields=('leave_request', 'approval_step', 'actor'),
                name='unique_decision_per_step_actor',
            ),
        ]

    def __str__(self):
        return f"Decision {self.decision} by {self.actor_id} on {self.leave_request_id} at {self.decided_at}"

    def save(self, *args, **kwargs):
        """Immutability guard: once created, an ApprovalDecision can never be updated."""
        if self.pk and not self._state.adding:
            raise ValidationError('Approval decisions are immutable and cannot be changed.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Approval decisions are immutable and cannot be deleted.')
