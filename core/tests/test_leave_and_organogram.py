from datetime import date, timedelta
from io import BytesIO
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from core.models import ApprovalDecision, Company, CompanyHoliday, CompanyWorkCalendar, Department, DeliveryJob, Employee, EmployeeRole, LeaveBalance, LeaveRequest, LeaveType, OrgUnit
from core.delivery import DeliveryService
from core.onboarding import ApprovalRoutingService, LeaveService
from zoho.models import EmailLog, EmployeeDocument


def next_working_day(days_ahead=1):
    candidate = date.today() + timedelta(days=days_ahead)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


class BaseModelTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme Corp")
        self.employee = Employee.objects.create_user(
            username="johndoe",
            email="john@acme.com",
            password="securepassword123",
            company=self.company
        )

    def test_uuid_generation(self):
        company2 = Company.objects.create(name="Stark Industries")
        self.assertIsNotNone(self.company.uuid)
        self.assertIsNotNone(company2.uuid)
        self.assertNotEqual(self.company.uuid, company2.uuid)

    def test_soft_delete(self):
        dept = Department.objects.create(
            name="Engineering",
            company=self.company,
            created_by=self.employee
        )
        dept_id = dept.id
        self.assertTrue(Department.objects.filter(id=dept_id).exists())
        dept.delete()
        self.assertFalse(Department.objects.filter(id=dept_id).exists())
        deleted_dept = Department.all_objects.get(id=dept_id)
        self.assertIsNotNone(deleted_dept.deleted_at)
        self.assertTrue(deleted_dept.deleted_at <= timezone.now())

    def test_hard_delete(self):
        dept = Department.objects.create(
            name="Marketing",
            company=self.company,
            created_by=self.employee
        )
        dept_id = dept.id
        dept.hard_delete()
        self.assertFalse(Department.objects.filter(id=dept_id).exists())
        self.assertFalse(Department.all_objects.filter(id=dept_id).exists())

    def test_company_scoped_relation(self):
        dept = Department.objects.create(name="HR", company=self.company)
        self.assertEqual(dept.company, self.company)
        self.assertIn(dept, self.company.department_records.all())


class HolidayCalendarTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Holiday Corp')

    def test_nigerian_public_holidays_are_excluded_happy_path(self):
        # 2026 Good Friday and Easter Monday mean this four-day period has no working leave day.
        self.assertEqual(LeaveService.calculate_working_days(date(2026, 4, 3), date(2026, 4, 6), self.company), 0)

    def test_company_holiday_is_excluded_boundary(self):
        CompanyHoliday.objects.create(company=self.company, name='Company retreat', date=date(2026, 6, 11))
        # 11 June is company closure, 12 June is Democracy Day, weekend follows; only 15 June counts.
        self.assertEqual(LeaveService.calculate_working_days(date(2026, 6, 11), date(2026, 6, 15), self.company), 1)

    def test_hr_can_configure_non_standard_work_week_happy_path(self):
        CompanyWorkCalendar.objects.create(
            company=self.company, working_weekdays=[6, 0, 1, 2, 3],
        )
        # Sunday is configured as a work day; Friday remains a non-working day.
        self.assertEqual(LeaveService.calculate_working_days(date(2026, 6, 14), date(2026, 6, 14), self.company), 1)
        self.assertEqual(LeaveService.calculate_working_days(date(2026, 6, 19), date(2026, 6, 19), self.company), 0)

    def test_national_holiday_policy_can_be_disabled_boundary(self):
        CompanyWorkCalendar.objects.create(
            company=self.company, working_weekdays=[4], include_nigerian_public_holidays=False,
        )
        # Friday 12 June is Democracy Day, but the explicit company policy disables national exclusions.
        self.assertEqual(LeaveService.calculate_working_days(date(2026, 6, 12), date(2026, 6, 12), self.company), 1)

    def test_work_calendar_rejects_invalid_weekday_error(self):
        with self.assertRaises(ValidationError):
            CompanyWorkCalendar.objects.create(company=self.company, working_weekdays=[0, 7])


@override_settings(ZOHO_USE_MOCK=True, DELIVERY_JOB_LEASE_SECONDS=60)
class DeliveryReliabilityTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Delivery Corp')
        self.employee = Employee.objects.create_user(
            username='delivery_admin', email='delivery@example.com', password='password123', company=self.company,
        )

    def create_email_job(self, **overrides):
        values = {
            'company': self.company,
            'kind': DeliveryJob.Kind.EMAIL,
            'payload': {'recipient': 'person@example.com', 'subject': 'Test', 'body': 'Hello', 'template_name': 'test'},
        }
        values.update(overrides)
        return DeliveryJob.objects.create(**values)

    def test_claim_processes_each_due_job_once_happy_path(self):
        job = self.create_email_job()
        with patch('core.delivery.ZohoMailService.send_and_log_email') as send:
            send.return_value = type('Log', (), {'status': 'SENT'})()
            claimed = DeliveryService.claim_next()
            DeliveryService.process(claimed)

        job.refresh_from_db()
        self.assertEqual(claimed.pk, job.pk)
        self.assertEqual(job.status, DeliveryJob.Status.SUCCEEDED)
        self.assertEqual(job.attempts, 1)
        self.assertIsNone(job.locked_at)
        self.assertIsNone(DeliveryService.claim_next())

    def test_stale_processing_job_is_reclaimed_boundary(self):
        job = self.create_email_job(
            status=DeliveryJob.Status.PROCESSING,
            locked_at=timezone.now() - timedelta(seconds=61),
        )
        claimed = DeliveryService.claim_next()
        self.assertEqual(claimed.pk, job.pk)
        self.assertEqual(claimed.attempts, 1)
        self.assertEqual(claimed.status, DeliveryJob.Status.PROCESSING)

    def test_failed_job_is_delayed_error(self):
        job = self.create_email_job()
        with patch('core.delivery.ZohoMailService.send_and_log_email', side_effect=RuntimeError('Zoho unavailable')):
            claimed = DeliveryService.claim_next()
            DeliveryService.process(claimed)

        job.refresh_from_db()
        self.assertEqual(job.status, DeliveryJob.Status.PENDING)
        self.assertEqual(job.attempts, 1)
        self.assertGreater(job.available_at, timezone.now())
        self.assertIn('Zoho unavailable', job.last_error)

    def test_third_failure_is_final_error(self):
        job = self.create_email_job(attempts=2)
        with override_settings(DELIVERY_FAILURE_ALERT_EMAIL='ops@example.com'):
            with patch('core.delivery.ZohoMailService.send_and_log_email', side_effect=RuntimeError('Zoho unavailable')):
                claimed = DeliveryService.claim_next()
                DeliveryService.process(claimed)

        job.refresh_from_db()
        self.assertEqual(job.status, DeliveryJob.Status.FAILED)
        self.assertEqual(job.attempts, 3)
        self.assertIsNone(job.locked_at)
        alert = DeliveryJob.objects.exclude(pk=job.pk).get()
        self.assertEqual(alert.payload['template_name'], 'delivery_failure_alert')


@override_settings(ZOHO_USE_MOCK=True)
class LeaveAndOrganogramTests(TestCase):

    def setUp(self):
        self.company = Company.objects.create(name="Infinity Corp")
        self.hr_admin = Employee.objects.create_user(
            username="hr_admin",
            email="hr@infinity.com",
            password="password123",
            company=self.company,
            role=EmployeeRole.HR_ADMIN,
        )
        self.admin = Employee.objects.create_user(
            username="admin",
            email="admin@infinity.com",
            password="password123",
            company=self.company,
            role=EmployeeRole.ADMIN,
        )
        self.exec_head = Employee.objects.create_user(
            username="exec_head",
            email="exec@infinity.com",
            password="password123",
            company=self.company,
            role=EmployeeRole.MANAGER,
        )
        self.supervisor = Employee.objects.create_user(
            username="supervisor",
            email="sup@infinity.com",
            password="password123",
            company=self.company,
            role=EmployeeRole.MANAGER,
        )

        self.division_unit = OrgUnit.objects.create(
            company=self.company,
            name="Executive Division",
            unit_type=OrgUnit.UnitType.DIVISION,
            head=self.exec_head,
        )
        self.dept_unit = OrgUnit.objects.create(
            company=self.company,
            name="Engineering Department",
            unit_type=OrgUnit.UnitType.DEPARTMENT,
            parent=self.division_unit,
            head=self.supervisor,
        )

        self.employee = Employee.objects.create_user(
            username="employee1",
            email="emp1@infinity.com",
            password="password123",
            company=self.company,
            role=EmployeeRole.EMPLOYEE,
            manager=self.supervisor,
            org_unit=self.dept_unit,
        )

        self.leave_type = LeaveType.objects.create(
            company=self.company,
            name="Annual Leave",
            default_days=20,
        )
        self.leave_balance = LeaveBalance.objects.create(
            company=self.company,
            employee=self.employee,
            leave_type=self.leave_type,
            allocated_days=20,
            used_days=0,
        )

        self.client = APIClient()

    @staticmethod
    def leave_document(name='supporting_note.pdf'):
        return SimpleUploadedFile(name, b'%PDF-1.4 supporting leave document', content_type='application/pdf')

    def test_leave_request_survives_workdrive_upload_failure(self):
        """A real leave request should still be created even if WorkDrive upload is unavailable."""
        doc_file = self.leave_document('medical_note.pdf')
        start = date.today() + timedelta(days=6)
        end = date.today() + timedelta(days=10)

        with patch('core.onboarding.ZohoWorkDriveService.upload_document', side_effect=RuntimeError('WorkDrive unavailable')):
            leave_req = LeaveService.request_leave(
                employee=self.employee,
                leave_type=self.leave_type,
                start_date=start,
                end_date=end,
                days_requested=5,
                reason='Medical recovery',
                document_file=doc_file,
            )

        self.assertEqual(leave_req.status, LeaveRequest.Status.PENDING_DEPARTMENT_HEAD)
        self.assertTrue(leave_req.document_name.endswith('.docx'))
        self.assertEqual(leave_req.supporting_document_name, 'medical_note.pdf')
        self.assertIsNone(leave_req.zoho_file_id)
        self.assertFalse(leave_req.workdrive_url)
        self.assertIsNone(leave_req.supporting_zoho_file_id)
        self.assertFalse(leave_req.supporting_workdrive_url)

    # --- HAPPY PATH TESTS ---
    def test_leave_request_creation_with_workdrive_document_happy_path(self):
        """Happy Path: Request leave with attached document, upload to WorkDrive, and trigger email logs."""
        doc_file = self.leave_document('medical_note.pdf')
        start = date.today() + timedelta(days=5)
        end = date.today() + timedelta(days=9)

        leave_req = LeaveService.request_leave(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date=start,
            end_date=end,
            days_requested=5,
            reason="Medical recovery",
            document_file=doc_file,
        )

        self.assertEqual(leave_req.status, LeaveRequest.Status.PENDING_DEPARTMENT_HEAD)
        self.assertTrue(leave_req.document_name.endswith(".docx"))
        self.assertEqual(leave_req.supporting_document_name, "medical_note.pdf")
        self.assertTrue(leave_req.zoho_file_id.startswith("mock_file_"))
        self.assertIn("workdrive.zoho.com", leave_req.workdrive_url)

        # Verify WorkDrive Document record
        doc_obj = EmployeeDocument.objects.filter(employee=self.employee, document_name="medical_note.pdf").first()
        self.assertIsNotNone(doc_obj)

        # Only the first (Department Head) stage is notified at submission.
        jobs = DeliveryJob.objects.filter(company=self.company, kind=DeliveryJob.Kind.EMAIL)
        self.assertEqual(jobs.count(), 1)
        self.assertEqual(jobs.first().payload['recipient'], 'sup@infinity.com')

    def test_organogram_routing_approvers_happy_path(self):
        """Happy Path: Organogram routing correctly builds 2-stage hierarchy (Dept Head -> HR)."""
        approvers = ApprovalRoutingService.get_leave_approvers(self.employee)
        approver_usernames = [a.username for a in approvers]
        self.assertEqual(approver_usernames, ["supervisor", "hr_admin"])

    def test_approval_stages_advance_in_order_happy_path(self):
        start = next_working_day(20)
        leave_req = LeaveService.request_leave(
            employee=self.employee, leave_type=self.leave_type, start_date=start,
            end_date=start, days_requested=1, reason="Family commitment", document_file=self.leave_document(),
        )
        self.assertEqual(leave_req.status, LeaveRequest.Status.PENDING_DEPARTMENT_HEAD)
        LeaveService.approve_leave(leave_req, self.supervisor, "Supervisor review complete")
        leave_req.refresh_from_db()
        self.assertEqual(leave_req.status, LeaveRequest.Status.PENDING_HR)
        LeaveService.approve_leave(leave_req, self.hr_admin, "HR review complete")
        leave_req.refresh_from_db()
        self.assertEqual(leave_req.status, LeaveRequest.Status.APPROVED)

    def test_amendment_request_restarts_approval_round_happy_path(self):
        start = next_working_day(20)
        leave_req = LeaveService.request_leave(
            employee=self.employee, leave_type=self.leave_type, start_date=start, end_date=start,
            days_requested=1, reason='Original reason', contact_during_leave='0800 111 2222',
            emergency_contact_name='Jane Doe', emergency_contact_phone='0700 111 2222',
            handover_contact='Colleague', handover_notes='Handover completed.',
        )
        LeaveService.request_amendment(leave_req, self.supervisor, 'Please provide a clearer reason.')
        leave_req.refresh_from_db()
        self.assertEqual(leave_req.status, LeaveRequest.Status.AMENDMENT_REQUESTED)
        self.assertEqual(leave_req.amendment_requested_by, self.supervisor)

        LeaveService.amend_leave(
            leave_req, self.employee, start_date=start, end_date=start, reason='Medical appointment',
            contact_during_leave='0800 111 2222', emergency_contact_name='Jane Doe',
            emergency_contact_phone='0700 111 2222', handover_contact='Colleague', handover_notes='Handover completed.',
        )
        leave_req.refresh_from_db()
        self.assertEqual(leave_req.status, LeaveRequest.Status.PENDING_DEPARTMENT_HEAD)
        self.assertEqual(leave_req.approval_round, 2)

    def test_hr_can_manage_document_policy_and_work_calendar_api(self):
        self.client.force_authenticate(user=self.hr_admin)
        leave_type_response = self.client.post('/api/leave-types/', {
            'name': 'Medical Leave', 'default_days': '10.0', 'requires_supporting_document': True,
        }, format='json')
        self.assertEqual(leave_type_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(leave_type_response.data['requires_supporting_document'])

        calendar_response = self.client.post('/api/work-calendars/', {
            'working_weekdays': [0, 1, 2, 3, 4], 'include_nigerian_public_holidays': True,
        }, format='json')
        self.assertEqual(calendar_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(calendar_response.data['working_weekdays'], [0, 1, 2, 3, 4])

        self.client.force_authenticate(user=self.employee)
        forbidden = self.client.post('/api/work-calendars/', {
            'working_weekdays': [0, 1, 2, 3, 4], 'include_nigerian_public_holidays': True,
        }, format='json')
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_insufficient_balance_blocks_final_approval(self):
        """Boundary: If the employee lacks enough remaining days, final approval must fail and not deduct balance."""
        self.leave_balance.allocated_days = 1
        self.leave_balance.used_days = 1
        self.leave_balance.save()

        start = next_working_day(40)
        leave_req = LeaveService.request_leave(
            employee=self.employee, leave_type=self.leave_type, start_date=start,
            end_date=start, days_requested=2, reason="Long trip", document_file=self.leave_document(),
        )

        LeaveService.approve_leave(leave_req, self.supervisor, "Supervisor ok")

        with self.assertRaises(ValidationError) as ctx:
            LeaveService.approve_leave(leave_req, self.hr_admin, "HR final")
        self.assertIn("Insufficient leave balance", str(ctx.exception))
        leave_req.refresh_from_db()
        self.assertEqual(leave_req.status, LeaveRequest.Status.PENDING_HR)

    def test_cancel_restores_used_days_after_approval(self):
        """When an already-approved leave is cancelled, the used_days on the balance should be restored."""
        days_until_monday = (7 - date.today().weekday()) % 7 or 7
        start = date.today() + timedelta(days=days_until_monday)
        leave_req = LeaveService.request_leave(
            employee=self.employee, leave_type=self.leave_type, start_date=start,
            end_date=start, days_requested=3, reason="Personal", document_file=self.leave_document(),
        )
        LeaveService.approve_leave(leave_req, self.supervisor, "Supervisor ok")
        LeaveService.approve_leave(leave_req, self.hr_admin, "HR ok")

        balance = LeaveBalance.objects.get(employee=self.employee, leave_type=self.leave_type)
        self.assertEqual(balance.used_days, 1)

        LeaveService.cancel_leave(leave_req, cancelled_by=self.employee)

        leave_req.refresh_from_db()
        balance.refresh_from_db()
        self.assertEqual(leave_req.status, LeaveRequest.Status.CANCELLED)
        self.assertEqual(balance.used_days, 0)

    def test_current_stage_cannot_be_skipped_error(self):
        start = next_working_day(25)
        leave_req = LeaveService.request_leave(
            employee=self.employee, leave_type=self.leave_type, start_date=start,
            end_date=start, days_requested=1, reason="Appointment", document_file=self.leave_document(),
        )
        with self.assertRaises(ValidationError) as ctx:
            LeaveService.approve_leave(leave_req, self.hr_admin, "Trying to skip stages")
        self.assertIn("not assigned to the current approval stage", str(ctx.exception))

    def test_cancel_permission_enforced(self):
        start = next_working_day(8)
        leave_req = LeaveService.request_leave(
            employee=self.employee, leave_type=self.leave_type, start_date=start,
            end_date=start, days_requested=1, reason="Test", document_file=self.leave_document(),
        )
        other_manager = Employee.objects.create_user(
            username="other_mgr2",
            email="other2@infinity.com",
            password='password',
            company=self.company,
            role=EmployeeRole.MANAGER,
        )
        self.client.force_authenticate(user=other_manager)
        response = self.client.post(f"/api/leave-requests/{leave_req.uuid}/cancel/")
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
        self.client.force_authenticate(user=self.employee)
        response = self.client.post(f"/api/leave-requests/{leave_req.uuid}/cancel/")
        self.assertEqual(response.status_code, 200)

    def test_approval_decisions_endpoint_permissions(self):
        start = next_working_day(22)
        leave_req = LeaveService.request_leave(
            employee=self.employee, leave_type=self.leave_type, start_date=start,
            end_date=start, days_requested=1, reason="Audit", document_file=self.leave_document(),
        )
        LeaveService.approve_leave(leave_req, self.supervisor, "Supervisor ok")

        self.client.force_authenticate(user=self.employee)
        response = self.client.get('/api/approval-decisions/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['decision'], 'APPROVED')

    def test_route_requires_hod_error(self):
        self.employee.org_unit = None
        self.employee.manager = None
        self.employee.save(update_fields=['org_unit', 'manager'])
        with self.assertRaises(ValidationError) as ctx:
            ApprovalRoutingService.build_route(self.employee)
        self.assertIn('no department head is configured', str(ctx.exception))

    def test_route_rejects_self_as_supervisor_error(self):
        self.employee.manager = self.employee
        self.employee.org_unit = None
        self.employee.save(update_fields=['manager', 'org_unit'])
        with self.assertRaises(ValidationError) as ctx:
            ApprovalRoutingService.build_route(self.employee)
        self.assertIn('no department head is configured', str(ctx.exception))
