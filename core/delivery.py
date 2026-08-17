import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.models import ApprovalDocument, DeliveryJob, Employee
from zoho.services import ZohoMailService, ZohoWorkDriveService


logger = logging.getLogger(__name__)


class DeliveryService:
    MAX_ATTEMPTS = 3

    @staticmethod
    def claim_next():
        """Atomically lease one due job so concurrent workers cannot duplicate it."""
        now = timezone.now()
        lease_expiry = now - timedelta(seconds=getattr(settings, 'DELIVERY_JOB_LEASE_SECONDS', 300))
        with transaction.atomic():
            job = (
                DeliveryJob.objects.select_for_update(skip_locked=True)
                .filter(
                    Q(status=DeliveryJob.Status.PENDING, available_at__lte=now)
                    | Q(status=DeliveryJob.Status.PROCESSING, locked_at__lt=lease_expiry)
                    | Q(status=DeliveryJob.Status.PROCESSING, locked_at__isnull=True)
                )
                .order_by('available_at', 'created_at')
                .first()
            )
            if job is None:
                return None
            job.status = DeliveryJob.Status.PROCESSING
            job.locked_at = now
            job.attempts += 1
            job.save(update_fields=['status', 'locked_at', 'attempts', 'updated_at'])
            return job

    @staticmethod
    def enqueue_email(*, company, recipient, subject, body, template_name, sent_by=None):
        return DeliveryJob.objects.create(
            company=company, kind=DeliveryJob.Kind.EMAIL,
            payload={'recipient': recipient, 'subject': subject, 'body': body, 'template_name': template_name, 'sent_by_id': sent_by.id if sent_by else None},
            created_by=sent_by, updated_by=sent_by,
        )

    @staticmethod
    def enqueue_approval_document(approval_document):
        return DeliveryJob.objects.create(
            company=approval_document.company, kind=DeliveryJob.Kind.APPROVAL_DOCUMENT,
            payload={'approval_document_id': approval_document.id},
            created_by=approval_document.created_by, updated_by=approval_document.created_by,
        )

    @staticmethod
    def process(job):
        """Run a previously claimed job. External calls intentionally happen without a DB lock."""
        if job.status != DeliveryJob.Status.PROCESSING:
            return job
        try:
            if job.kind == DeliveryJob.Kind.EMAIL:
                payload = job.payload
                log = ZohoMailService.send_and_log_email(
                    company=job.company, recipient=payload['recipient'], subject=payload['subject'], body=payload['body'],
                    template_name=payload['template_name'],
                    sent_by=Employee.objects.filter(pk=payload.get('sent_by_id')).first(),
                )
                if log.status != 'SENT':
                    raise RuntimeError(log.status)
            elif job.kind == DeliveryJob.Kind.APPROVAL_DOCUMENT:
                document = ApprovalDocument.objects.select_related('leave_request__employee').get(pk=job.payload['approval_document_id'])
                # A completed upload is idempotent: a re-run must never create a second file.
                if not document.zoho_file_id:
                    leave_request = document.leave_request
                    folder = leave_request.employee.workdrive_folder
                    workdrive_service = ZohoWorkDriveService()

                    # Check if file already exists remotely to prevent orphans
                    existing_file_id = None
                    if folder and getattr(folder, 'zoho_folder_id', None):
                        existing_file_id = workdrive_service.find_file_by_name(folder.zoho_folder_id, document.file_name)

                    if existing_file_id:
                        document.zoho_file_id = existing_file_id
                    else:
                        with open(document.file_path, 'rb') as source:
                            uploaded = workdrive_service.upload_document(
                                employee=leave_request.employee, folder=folder,
                                document_name=document.file_name, document_type='docx', file_content=source.read(), uploaded_by=document.created_by,
                            )
                        document.zoho_file_id = uploaded.zoho_file_id

                with transaction.atomic():
                    document.upload_status = 'SUCCEEDED'
                    document.upload_error = ''
                    document.save(update_fields=['zoho_file_id', 'upload_status', 'upload_error', 'updated_at'])
            job.status = DeliveryJob.Status.SUCCEEDED
            job.completed_at = timezone.now()
            job.last_error = ''
            job.locked_at = None
        except Exception as exc:
            if job.kind == DeliveryJob.Kind.APPROVAL_DOCUMENT:
                ApprovalDocument.objects.filter(pk=job.payload.get('approval_document_id')).update(
                    upload_status='FAILED' if job.attempts >= DeliveryService.MAX_ATTEMPTS else 'PENDING', upload_error=str(exc)[:1000],
                )
            job.last_error = str(exc)[:1000]
            job.status = DeliveryJob.Status.FAILED if job.attempts >= DeliveryService.MAX_ATTEMPTS else DeliveryJob.Status.PENDING
            job.locked_at = None
            if job.status == DeliveryJob.Status.PENDING:
                delay_minutes = min(2 ** (job.attempts - 1), 60)
                job.available_at = timezone.now() + timedelta(minutes=delay_minutes)
            elif job.payload.get('template_name') != 'delivery_failure_alert':
                alert_recipient = getattr(settings, 'DELIVERY_FAILURE_ALERT_EMAIL', '')
                if alert_recipient:
                    try:
                        DeliveryService.enqueue_email(
                            company=job.company,
                            recipient=alert_recipient,
                            subject=f'HR platform delivery failed: {job.kind}',
                            body=f'Delivery job {job.uuid} failed after {job.attempts} attempts. Error: {job.last_error}',
                            template_name='delivery_failure_alert',
                        )
                    except Exception:
                        logger.exception('Could not queue failure alert for delivery job %s', job.uuid)
            logger.exception('Delivery job %s failed on attempt %s', job.uuid, job.attempts)
        job.save(update_fields=['status', 'completed_at', 'last_error', 'available_at', 'locked_at', 'updated_at'])
        return job
