from django.db import models

from .base import CompanyScopedModel


class LeaveType(CompanyScopedModel):
    name = models.CharField(max_length=100)
    default_days = models.DecimalField(max_digits=5, decimal_places=1)

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
    allocated_days = models.DecimalField(max_digits=5, decimal_places=1)
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        db_table = 'leave_balances'
        unique_together = ('employee', 'leave_type')

    def __str__(self):
        return f"{self.employee.username} - {self.leave_type.name}"

    @property
    def remaining_days(self):
        return self.allocated_days - self.used_days


class LeaveRequest(CompanyScopedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

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
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
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
