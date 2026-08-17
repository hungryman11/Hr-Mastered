from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

import openpyxl
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from core.management.commands.seed_demo import DEMO_COMPANY
from core.models import (
    Company, Department, Employee, EmployeeKpiAssignment, LeaveApprovalStep,
    LeaveRequest, PerformanceReview, Position, SalaryRecord,
)


class DemoSeedTests(TestCase):
    def seed(self):
        call_command('seed_demo', stdout=StringIO())

    def test_seed_is_idempotent_and_provisions_uat_data(self):
        self.seed()
        self.seed()
        company = Company.objects.get(name=DEMO_COMPANY)
        self.assertEqual(Employee.objects.filter(company=company, username__startswith='demo.').count(), 8)
        employee = Employee.objects.get(company=company, username='demo.employee')
        self.assertEqual(employee.manager.username, 'demo.manager')
        self.assertTrue(employee.is_active)
        self.assertTrue(LeaveRequest.objects.filter(company=company, employee=employee).exists())
        leave = LeaveRequest.objects.get(company=company, employee=employee)
        self.assertTrue(LeaveApprovalStep.objects.filter(leave_request=leave).exists())
        self.assertEqual(EmployeeKpiAssignment.objects.filter(company=company, employee=employee).count(), 3)
        self.assertTrue(PerformanceReview.objects.filter(company=company, employee=employee).exists())
        self.assertTrue(SalaryRecord.objects.filter(company=company, employee=employee).exists())

    def test_seed_is_isolated_from_other_companies(self):
        other = Company.objects.create(name='Other tenant')
        Employee.objects.create_user(username='other.user', password='x', email='other@example.test', company=other)
        self.seed()
        self.assertEqual(Employee.objects.filter(company=other).count(), 1)

    @override_settings(DEBUG=True)
    def test_debug_demo_login_creates_regular_session(self):
        self.seed()
        for username, expected_role, permitted_path in (
            ('demo.hr.admin', 'HR_ADMIN', '/api/kpi-templates/'),
            ('demo.employee', 'EMPLOYEE', '/api/salary-records/current/'),
            ('demo.manager', 'MANAGER', '/api/leave-requests/'),
            ('demo.finance', 'FINANCE', '/api/payroll-profiles/'),
        ):
            client = Client(enforce_csrf_checks=True)
            response = client.get('/api/demo-auth/users/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()['users']), 8)
            self.assertTrue(response.json()['csrf_token'])
            response = client.post(
                '/api/demo-auth/login/', data=f'{{"username":"{username}"}}', content_type='application/json',
                HTTP_X_CSRFTOKEN=response.json()['csrf_token'],
            )
            self.assertEqual(response.status_code, 200)
            current_user = client.get('/api/employees/me/')
            self.assertEqual(current_user.status_code, 200)
            self.assertEqual(current_user.json()['username'], username)
            self.assertEqual(current_user.json()['role'], expected_role)
            self.assertEqual(client.get(permitted_path).status_code, 200)
            if username == 'demo.employee':
                self.assertEqual(client.get('/api/payroll-profiles/').status_code, 403)

    @override_settings(DEBUG=True)
    def test_demo_login_parses_json_with_an_ignored_password_field(self):
        self.seed()
        client = Client(enforce_csrf_checks=True)
        response = client.get('/api/demo-auth/users/')
        response = client.post(
            '/api/demo-auth/login/', data='{"username":"demo.hr.admin","password":"DemoPass123!"}',
            content_type='application/json', HTTP_X_CSRFTOKEN=response.json()['csrf_token'],
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(DEBUG=False)
    def test_demo_login_is_disabled_outside_debug(self):
        self.assertEqual(self.client.get('/api/demo-auth/users/').status_code, 404)


class InfinityStaffImportTests(TestCase):
    def make_workbook(self, rows):
        handle = NamedTemporaryFile(suffix='.xlsx', delete=False)
        handle.close()
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        headers = ['STAFF ID NO.', 'FULL NAME', 'DESIGNATION', 'DEPARTMENT', 'EMAIL', 'STATUS']
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
        workbook.save(handle.name)
        return Path(handle.name)

    def setUp(self):
        self.company = Company.objects.create(name='Importer Test Company')
        self.department = Department.objects.create(company=self.company, name='Operations')
        self.position = Position.objects.create(company=self.company, title='Operations Officer')

    def test_dry_run_reports_findings_and_writes_nothing(self):
        path = self.make_workbook([
            ['IMFB/1', 'Valid Person', 'Operations Officer', 'Operations', 'valid@infinitymfb.com', 'PERMANENT'],
            ['IMFB/2', 'No Email', 'Operations Officer', 'Operations', 'N/A', 'PERMANENT'],
            ['IMFB/3', 'Duplicate', 'Operations Officer', 'Operations', 'valid@infinitymfb.com', 'PERMANENT'],
            ['IMFB/4', 'Bad Mapping', 'Unknown', 'Unknown', 'mapped@infinitymfb.com', 'PERMANENT'],
        ])
        output = StringIO()
        try:
            call_command('import_infinity_staff', str(path), '--company', self.company.name, '--dry-run', stdout=output)
        finally:
            path.unlink(missing_ok=True)
        text = output.getvalue()
        self.assertIn('fully_mapped_rows=1', text)
        self.assertIn('missing_or_invalid_email=1', text)
        self.assertIn('duplicate_email_in_workbook=1', text)
        self.assertIn('unmapped_department=1', text)
        self.assertEqual(Employee.objects.filter(company=self.company).count(), 0)

    def test_commit_is_idempotent_and_never_sets_zoho_identity(self):
        path = self.make_workbook([['IMFB/1', 'Valid Person', 'Operations Officer', 'Operations', 'valid@infinitymfb.com', 'PERMANENT']])
        try:
            call_command('import_infinity_staff', str(path), '--company', self.company.name, '--commit', stdout=StringIO())
            call_command('import_infinity_staff', str(path), '--company', self.company.name, '--commit', stdout=StringIO())
        finally:
            path.unlink(missing_ok=True)
        employee = Employee.objects.get(company=self.company, email='valid@infinitymfb.com')
        self.assertIsNone(employee.zoho_user_id)
        self.assertEqual(Employee.objects.filter(company=self.company).count(), 1)
        self.assertEqual(employee.payroll_profile.employee_number, 'IMFB/1')
