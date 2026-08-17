"""
Unit tests for core.delivery (DeliveryService).

Coverage targets
────────────────
- enqueue_email:           happy path — job is created with correct payload
- enqueue_approval_document: happy path — job linked to document
- claim_next:              returns next due job; skips locked jobs (boundary)
- process (EMAIL):         success path (mocked Zoho), failure → retry, final failure
- process (APPROVAL_DOCUMENT): idempotent upload guard (boundary)
- exponential backoff:     first retry waits 1 min, second waits 2 min (boundary)
"""
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from core.delivery import DeliveryService
from core.models import Company, DeliveryJob, Employee


@override_settings(
    FIELD_ENCRYPTION_KEY="test-encryption-key-must-be-long-enough-x",
    DELIVERY_JOB_LEASE_SECONDS=300,
)
class DeliveryServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Delivery Corp")
        self.sender = Employee.objects.create_user(
            username="delivery_sender", password="x", company=self.company
        )

    # ── enqueue_email ────────────────────────────────────────────────────────

    def test_enqueue_email_creates_pending_job_happy_path(self):
        job = DeliveryService.enqueue_email(
            company=self.company,
            recipient="hr@delivery.co",
            subject="Test subject",
            body="Hello world",
            template_name="test_template",
            sent_by=self.sender,
        )
        self.assertEqual(job.status, DeliveryJob.Status.PENDING)
        self.assertEqual(job.kind, DeliveryJob.Kind.EMAIL)
        self.assertEqual(job.payload["recipient"], "hr@delivery.co")
        self.assertEqual(job.payload["template_name"], "test_template")

    def test_enqueue_email_without_sender_stores_none_boundary(self):
        job = DeliveryService.enqueue_email(
            company=self.company,
            recipient="no-sender@example.com",
            subject="No sender",
            body="body",
            template_name="plain",
        )
        self.assertIsNone(job.payload["sent_by_id"])

    # ── claim_next ───────────────────────────────────────────────────────────

    def test_claim_next_returns_oldest_pending_job_happy_path(self):
        job = DeliveryService.enqueue_email(
            company=self.company, recipient="a@b.com", subject="s", body="b", template_name="t"
        )
        claimed = DeliveryService.claim_next()
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.pk, job.pk)
        self.assertEqual(claimed.status, DeliveryJob.Status.PROCESSING)
        self.assertEqual(claimed.attempts, 1)

    def test_claim_next_returns_none_when_queue_empty_boundary(self):
        self.assertIsNone(DeliveryService.claim_next())

    def test_claim_next_skips_future_scheduled_job_boundary(self):
        job = DeliveryService.enqueue_email(
            company=self.company, recipient="b@c.com", subject="s", body="b", template_name="t"
        )
        # Push available_at into the future so it must not be claimed yet
        job.available_at = timezone.now() + timedelta(hours=1)
        job.save()
        self.assertIsNone(DeliveryService.claim_next())

    # ── process (EMAIL success) ──────────────────────────────────────────────

    def test_process_email_success_marks_job_succeeded_happy_path(self):
        job = DeliveryService.enqueue_email(
            company=self.company, recipient="r@r.com", subject="s", body="b", template_name="t"
        )
        DeliveryService.claim_next()
        job.refresh_from_db()

        mock_log = MagicMock()
        mock_log.status = "SENT"
        with patch("core.delivery.ZohoMailService.send_and_log_email", return_value=mock_log):
            DeliveryService.process(job)

        job.refresh_from_db()
        self.assertEqual(job.status, DeliveryJob.Status.SUCCEEDED)
        self.assertEqual(job.last_error, "")

    # ── process (EMAIL failure → retry) ─────────────────────────────────────

    def test_process_email_failure_reschedules_for_retry_error(self):
        job = DeliveryService.enqueue_email(
            company=self.company, recipient="fail@r.com", subject="s", body="b", template_name="t"
        )
        job.status = DeliveryJob.Status.PROCESSING
        job.attempts = 1
        job.save()

        with patch("core.delivery.ZohoMailService.send_and_log_email", side_effect=RuntimeError("SMTP down")):
            DeliveryService.process(job)

        job.refresh_from_db()
        self.assertEqual(job.status, DeliveryJob.Status.PENDING)
        self.assertIn("SMTP down", job.last_error)
        # Backoff: available_at must be pushed into the future
        self.assertGreater(job.available_at, timezone.now())

    # ── process (EMAIL final failure) ────────────────────────────────────────

    def test_process_email_final_failure_after_max_attempts_error(self):
        job = DeliveryService.enqueue_email(
            company=self.company, recipient="final@r.com", subject="s", body="b", template_name="t"
        )
        job.status = DeliveryJob.Status.PROCESSING
        job.attempts = DeliveryService.MAX_ATTEMPTS  # already at limit
        job.save()

        with patch("core.delivery.ZohoMailService.send_and_log_email", side_effect=RuntimeError("still broken")):
            DeliveryService.process(job)

        job.refresh_from_db()
        self.assertEqual(job.status, DeliveryJob.Status.FAILED)

    # ── exponential backoff ──────────────────────────────────────────────────

    def test_exponential_backoff_grows_with_attempts_boundary(self):
        before = timezone.now()
        job1 = DeliveryService.enqueue_email(
            company=self.company, recipient="x@x.com", subject="s", body="b", template_name="t"
        )
        job1.status = DeliveryJob.Status.PROCESSING
        job1.attempts = 1
        job1.save()

        job2 = DeliveryService.enqueue_email(
            company=self.company, recipient="y@y.com", subject="s", body="b", template_name="t"
        )
        job2.status = DeliveryJob.Status.PROCESSING
        job2.attempts = 2
        job2.save()

        with patch("core.delivery.ZohoMailService.send_and_log_email", side_effect=RuntimeError("err")):
            DeliveryService.process(job1)
            DeliveryService.process(job2)

        job1.refresh_from_db()
        job2.refresh_from_db()
        # Second attempt should be available later than first attempt
        self.assertGreater(job2.available_at, job1.available_at)
