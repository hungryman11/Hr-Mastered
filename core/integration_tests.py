"""
Integration tests for the Payroll and Loan API endpoints.

These tests exercise the full Django request/response stack — serializers,
permission classes, service layer, and database — so they verify that the
wiring between all layers is correct.

Test taxonomy
─────────────
happy_path:  request succeeds and response shape matches the API contract
boundary:    request at the edge of a valid / invalid boundary
error:       request that should be rejected with an appropriate status code
"""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Company,
    Employee,
    EmployeeRole,
    PayrollAdjustment,
    PayrollConfig,
    PayrollProfile,
    PayrollRun,
    StatutoryRule,
)
from core.payroll import PayrollService


# ═══════════════════════════════════════════════════════════════════════════════
# Payroll profile API
# ═══════════════════════════════════════════════════════════════════════════════


class PayrollProfileApiTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Profile API Co")
        self.hr = Employee.objects.create_user(
            username="prof_hr", password="x", company=self.company, role=EmployeeRole.HR_ADMIN
        )
        self.employee = Employee.objects.create_user(
            username="prof_emp", password="x", company=self.company
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.hr)

    def test_list_profiles_returns_only_company_profiles_happy_path(self):
        PayrollProfile.objects.create(
            company=self.company,
            employee=self.employee,
            employee_number="E001",
            base_salary=Decimal("80000"),
            hire_date=date(2025, 1, 1),
        )
        other_company = Company.objects.create(name="Other Co")
        other_emp = Employee.objects.create_user(username="other_emp", password="x", company=other_company)
        PayrollProfile.objects.create(
            company=other_company,
            employee=other_emp,
            employee_number="X001",
            base_salary=Decimal("50000"),
            hire_date=date(2025, 1, 1),
        )
        resp = self.client.get("/api/payroll-profiles/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        uuids = {r["employee_number"] for r in resp.data}
        self.assertIn("E001", uuids)
        self.assertNotIn("X001", uuids)

    def test_create_profile_for_company_employee_happy_path(self):
        resp = self.client.post(
            "/api/payroll-profiles/",
            {
                "employee": str(self.employee.uuid),
                "employee_number": "E002",
                "base_salary": "75000.00",
                "bank_code": "058",
                "hire_date": "2025-03-01",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["employee_number"], "E002")

    def test_regular_employee_cannot_create_profile_error(self):
        plain_emp = Employee.objects.create_user(
            username="plain_emp", password="x", company=self.company, role=EmployeeRole.EMPLOYEE
        )
        self.client.force_authenticate(user=plain_emp)
        resp = self.client.post(
            "/api/payroll-profiles/",
            {"employee": str(self.employee.uuid), "employee_number": "E003", "base_salary": "10000", "hire_date": "2025-01-01"},
            format="json",
        )
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])

    def test_validate_csv_endpoint_reports_bad_rows_boundary(self):
        import io
        csv_content = (
            "employee_number,base_salary,bank_code,hire_date\n"
            "E001,100000,058,2025-01-01\n"
            "BAD,0,abc,2025-01-01\n"
        )
        csv_file = io.BytesIO(csv_content.encode())
        csv_file.name = "test.csv"
        resp = self.client.post(
            "/api/payroll-profiles/validate_csv/",
            {"file": csv_file},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["valid_rows"], 1)
        self.assertEqual(len(resp.data["errors"]), 1)


# ═══════════════════════════════════════════════════════════════════════════════
# Payroll run workflow API
# ═══════════════════════════════════════════════════════════════════════════════


class PayrollRunApiTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Run API Co")
        self.hr = Employee.objects.create_user(
            username="run_hr", password="x", company=self.company, role=EmployeeRole.HR_ADMIN
        )
        self.finance = Employee.objects.create_user(
            username="run_finance", password="x", company=self.company, role=EmployeeRole.FINANCE
        )
        self.employee = Employee.objects.create_user(
            username="run_emp", password="x", company=self.company
        )
        PayrollProfile.objects.create(
            company=self.company,
            employee=self.employee,
            employee_number="E001",
            base_salary=Decimal("120000"),
            bank_account_ciphertext="encrypted-acc",
            bank_code="057",
            hire_date=date(2025, 1, 1),
        )
        PayrollConfig.objects.create(
            company=self.company,
            maximum_deduction_percent=Decimal("30"),
            settlement_formats=["CSV"],
        )
        self.run = PayrollRun.objects.create(
            company=self.company, month=date(2026, 6, 1), created_by=self.hr
        )
        self.client = APIClient()

    def test_hr_can_trigger_calculate_action_happy_path(self):
        self.client.force_authenticate(user=self.hr)
        resp = self.client.post(f"/api/payroll-runs/{self.run.uuid}/calculate/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "CALCULATED")

    def test_finance_can_review_and_approve_run_happy_path(self):
        PayrollService.calculate(self.run, self.hr)
        self.client.force_authenticate(user=self.finance)
        resp = self.client.post(f"/api/payroll-runs/{self.run.uuid}/review/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "REVIEWED")

        resp = self.client.post(f"/api/payroll-runs/{self.run.uuid}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "APPROVED")

    def test_cross_company_user_cannot_access_run_error(self):
        other_company = Company.objects.create(name="Intruder Co")
        intruder = Employee.objects.create_user(
            username="intruder", password="x", company=other_company, role=EmployeeRole.FINANCE
        )
        self.client.force_authenticate(user=intruder)
        resp = self.client.post(f"/api/payroll-runs/{self.run.uuid}/calculate/")
        # Service will raise ValidationError → 400, or not found → 404
        self.assertIn(resp.status_code, [400, 403, 404])

    def test_list_runs_scoped_to_company_boundary(self):
        other_company = Company.objects.create(name="Scope Co")
        other_hr = Employee.objects.create_user(
            username="scope_hr", password="x", company=other_company, role=EmployeeRole.HR_ADMIN
        )
        PayrollRun.objects.create(company=other_company, month=date(2026, 5, 1), created_by=other_hr)
        self.client.force_authenticate(user=self.hr)
        resp = self.client.get("/api/payroll-runs/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        company_ids = {r["uuid"] for r in resp.data}
        # Our run must appear
        self.assertIn(str(self.run.uuid), company_ids)
        # Other company's run must NOT appear
        other_run = PayrollRun.objects.get(company=other_company)
        self.assertNotIn(str(other_run.uuid), company_ids)


# ═══════════════════════════════════════════════════════════════════════════════
# Deduction contest / resolve API
# ═══════════════════════════════════════════════════════════════════════════════


class DeductionApiTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Deduction API Co")
        self.hr = Employee.objects.create_user(
            username="ded_hr", password="x", company=self.company, role=EmployeeRole.HR_ADMIN
        )
        self.finance = Employee.objects.create_user(
            username="ded_finance", password="x", company=self.company, role=EmployeeRole.FINANCE
        )
        self.employee = Employee.objects.create_user(
            username="ded_emp", password="x", company=self.company
        )
        PayrollProfile.objects.create(
            company=self.company,
            employee=self.employee,
            employee_number="D001",
            base_salary=Decimal("60000"),
            bank_account_ciphertext="enc-acc",
            bank_code="033",
            hire_date=date(2025, 1, 1),
        )
        PayrollConfig.objects.create(
            company=self.company,
            maximum_deduction_percent=Decimal("50"),
            settlement_formats=["CSV"],
        )
        adj = PayrollAdjustment.objects.create(
            company=self.company,
            employee=self.employee,
            kind="CUSTOM",
            name="Late arrival",
            amount=Decimal("3000"),
            month=date(2026, 6, 1),
            reason="Three lates in June.",
            status="APPROVED",
        )
        self.run = PayrollRun.objects.create(
            company=self.company, month=date(2026, 6, 1), created_by=self.hr
        )
        PayrollService.calculate(self.run, self.hr)
        self.deduction = self.run.items.get().deductions.get(adjustment=adj)
        self.client = APIClient()

    def test_employee_contests_own_deduction_happy_path(self):
        self.client.force_authenticate(user=self.employee)
        resp = self.client.post(
            f"/api/payroll-deductions/{self.deduction.uuid}/contest/",
            {"reason": "I was not late on these dates."},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["is_held"])

    def test_finance_resolves_contested_deduction_happy_path(self):
        from core.payroll import PayrollService as PS
        PS.contest_deduction(self.deduction, self.employee, "Dispute reason.")
        self.client.force_authenticate(user=self.finance)
        resp = self.client.post(
            f"/api/payroll-deductions/{self.deduction.uuid}/resolve/",
            {"uphold": False, "notes": "Verified — deduction is removed."},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(resp.data["amount"]), Decimal("0.00"))

    def test_empty_contest_reason_is_rejected_error(self):
        self.client.force_authenticate(user=self.employee)
        resp = self.client.post(
            f"/api/payroll-deductions/{self.deduction.uuid}/contest/",
            {"reason": ""},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)



