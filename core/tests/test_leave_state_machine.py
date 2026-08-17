from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import (
    ApprovalDecision,
    ApprovalDelegation,
    Company,
    CompanyWorkCalendar,
    Employee,
    EmployeeRole,
    LeaveBalance,
    LeaveApprovalStep,
    LeaveRequest,
    LeaveType,
    OrgUnit,
)
from core.onboarding import ApprovalRoutingService, LeaveService


def next_working_day(days_ahead=1):
    candidate = date.today() + timedelta(days=days_ahead)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


@override_settings(ZOHO_USE_MOCK=True)
class LeaveStateMachineTests(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(name="Company Alpha")
        self.company_b = Company.objects.create(name="Company Beta")
        # Disable Nigerian public holidays for test companies to avoid test date conflicts
        CompanyWorkCalendar.objects.create(company=self.company_a, include_nigerian_public_holidays=False)
        CompanyWorkCalendar.objects.create(company=self.company_b, include_nigerian_public_holidays=False)

        self.hr_admin_a = Employee.objects.create_user(
            username="hr_alpha",
            email="hr@alpha.com",
            password="password123",
            company=self.company_a,
            role=EmployeeRole.HR_ADMIN,
        )

        self.dept_head_a = Employee.objects.create_user(
            username="head_alpha",
            email="head@alpha.com",
            password="password123",
            company=self.company_a,
            role=EmployeeRole.MANAGER,
        )

        self.dept_unit_a = OrgUnit.objects.create(
            company=self.company_a,
            name="Engineering Alpha",
            unit_type=OrgUnit.UnitType.DEPARTMENT,
            head=self.dept_head_a,
        )

        self.employee_a = Employee.objects.create_user(
            username="emp_alpha",
            email="emp@alpha.com",
            password="password123",
            company=self.company_a,
            role=EmployeeRole.EMPLOYEE,
            org_unit=self.dept_unit_a,
        )

        self.leave_type_a = LeaveType.objects.create(
            company=self.company_a,
            name="Annual Leave",
            default_days=20,
        )
        self.leave_balance_a = LeaveBalance.objects.create(
            company=self.company_a,
            employee=self.employee_a,
            leave_type=self.leave_type_a,
            allocated_days=20,
            used_days=0,
        )

        self.client = APIClient()

    def test_two_stage_leave_approval_workflow(self):
        """Verify two-stage approval: PENDING_DEPARTMENT_HEAD -> Dept Head approves -> PENDING_HR -> HR approves -> APPROVED."""
        start = next_working_day(10)
        leave_req = LeaveService.request_leave(
            employee=self.employee_a,
            leave_type=self.leave_type_a,
            start_date=start,
            end_date=start,
            days_requested=1,
            reason="Visiting family",
            contact_during_leave="0800123456",
            emergency_contact_name="Emergency",
            emergency_contact_phone="0800999999",
            handover_contact="Colleague",
            handover_notes="Done",
        )

        self.assertEqual(leave_req.status, LeaveRequest.Status.PENDING_DEPARTMENT_HEAD)

        # Department Head approves
        LeaveService.approve_leave(leave_req, self.dept_head_a, "Dept Head Approved")
        leave_req.refresh_from_db()
        self.assertEqual(leave_req.status, LeaveRequest.Status.PENDING_HR)

        # HR Admin approves
        LeaveService.approve_leave(leave_req, self.hr_admin_a, "HR Approved")
        leave_req.refresh_from_db()
        self.assertEqual(leave_req.status, LeaveRequest.Status.APPROVED)

    def test_pending_approval_queue_only_returns_current_assignee(self):
        start = next_working_day(10)
        leave_req = LeaveService.request_leave(
            employee=self.employee_a, leave_type=self.leave_type_a,
            start_date=start, end_date=start, days_requested=1,
            reason='Family event', contact_during_leave='0800123456',
            emergency_contact_name='Emergency', emergency_contact_phone='0800999999',
            handover_contact='Colleague', handover_notes='Done',
        )
        self.client.force_authenticate(user=self.dept_head_a)
        response = self.client.get('/api/leave-requests/pending-approvals/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['uuid'] for row in response.data], [str(leave_req.uuid)])
        self.assertTrue(response.data[0]['can_approve'])
        self.assertEqual(response.data[0]['current_approval_step']['stage'], 'DEPT_HEAD')

        self.client.force_authenticate(user=self.hr_admin_a)
        self.assertEqual(self.client.get('/api/leave-requests/pending-approvals/').data, [])

        LeaveService.approve_leave(leave_req, self.dept_head_a, 'Approved')
        response = self.client.get('/api/leave-requests/pending-approvals/')
        self.assertEqual([row['uuid'] for row in response.data], [str(leave_req.uuid)])
        self.assertEqual(response.data[0]['current_approval_step']['stage'], 'HR')

    def test_delegation_same_company_guard(self):
        """Verify that approval delegation across different companies is ignored/guarded."""
        delegate_other_company = Employee.objects.create_user(
            username="emp_beta",
            email="emp@beta.com",
            password="password123",
            company=self.company_b,
            role=EmployeeRole.MANAGER,
        )

        # Create malicious cross-company delegation
        ApprovalDelegation.objects.create(
            company=self.company_a,
            approver=self.dept_head_a,
            delegate_to=delegate_other_company,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=5),
            active=True,
        )

        # Build route for employee_a — cross-company delegate must be ignored and dept_head_a retained
        approvers = ApprovalRoutingService.get_leave_approvers(self.employee_a)
        self.assertIn(self.dept_head_a, approvers)
        self.assertNotIn(delegate_other_company, approvers)

    def test_missing_department_head_error(self):
        """Verify explicit ValidationError when employee has no configured department head."""
        orphan_employee = Employee.objects.create_user(
            username="orphan_emp",
            email="orphan@alpha.com",
            password="password123",
            company=self.company_a,
            role=EmployeeRole.EMPLOYEE,
        )

        start = next_working_day(5)
        with self.assertRaises(ValidationError) as ctx:
            LeaveService.request_leave(
                employee=orphan_employee,
                leave_type=self.leave_type_a,
                start_date=start,
                end_date=start,
                days_requested=1,
                reason="Trip",
                contact_during_leave="0800123456",
                emergency_contact_name="Emergency",
                emergency_contact_phone="0800999999",
                handover_contact="Colleague",
                handover_notes="Done",
            )
        self.assertIn("no department head is configured", str(ctx.exception))

    def test_approval_decision_immutability(self):
        """Verify that ApprovalDecision records cannot be updated or deleted."""
        start = next_working_day(12)
        leave_req = LeaveService.request_leave(
            employee=self.employee_a,
            leave_type=self.leave_type_a,
            start_date=start,
            end_date=start,
            days_requested=1,
            reason="Medical",
            contact_during_leave="0800123456",
            emergency_contact_name="Emergency",
            emergency_contact_phone="0800999999",
            handover_contact="Colleague",
            handover_notes="Done",
        )
        LeaveService.approve_leave(leave_req, self.dept_head_a, "Dept Head Approved")

        decision = ApprovalDecision.objects.filter(leave_request=leave_req).first()
        self.assertIsNotNone(decision)

        # Attempt to modify decision
        decision.reason = "Tampered reason"
        with self.assertRaises(ValidationError) as ctx:
            decision.save()
        self.assertIn("immutable", str(ctx.exception))

        # Attempt to delete decision
        with self.assertRaises(ValidationError) as ctx:
            decision.delete()
        self.assertIn("immutable", str(ctx.exception))
