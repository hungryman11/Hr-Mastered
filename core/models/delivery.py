from django.db import models
from django.utils import timezone

from .base import CompanyScopedModel


class DeliveryJob(CompanyScopedModel):
    class Kind(models.TextChoices):
        EMAIL = 'EMAIL', 'Email'
        APPROVAL_DOCUMENT = 'APPROVAL_DOCUMENT', 'Approval document upload'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        SUCCEEDED = 'SUCCEEDED', 'Succeeded'
        FAILED = 'FAILED', 'Failed'

    kind = models.CharField(max_length=30, choices=Kind.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payload = models.JSONField()
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    available_at = models.DateTimeField(default=timezone.now)
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'delivery_jobs'
        indexes = [
            models.Index(fields=('status', 'created_at')),
            models.Index(fields=('status', 'available_at'), name='delivery_status_available_idx'),
        ]
