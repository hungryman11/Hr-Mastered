import csv
import io
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from pathlib import Path

from core.models import Company, Employee, EmployeeRole, PayrollAdjustment, PayrollConfig, PayrollProfile, PayrollRun, StatutoryRule
from core.payroll import PayrollService
from core.payroll_import import PayrollImportService


class PayrollCalculationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Payroll Co')
        self.hr = Employee.objects.create_user(username='payroll_hr', password='x', company=self.company, role=EmployeeRole.HR_ADMIN)
        self.finance = Employee.objects.create_user(username='payroll_finance', password='x', company=self.company, role=EmployeeRole.FINANCE)
        self.employee = Employee.objects.create_user(username='payroll_employee', password='x', company=self.company)
        self.profile = PayrollProfile.objects.create(company=self.company, employee=self.employee, employee_number='E001', base_salary=Decimal('100000.00'), bank_account_ciphertext='encrypted-account', bank_code='058', hire_date=date(2025, 1, 1))
        PayrollConfig.objects.create(company=self.company, maximum_deduction_percent=Decimal('100.00'), settlement_formats=['CSV'])
        self.run = PayrollRun.objects.create(company=self.company, month=date(2026, 7, 1), created_by=self.hr)

    def test_calculates_statutory_and_approved_deduction_happy_path(self):
        StatutoryRule.objects.create(company=self.company, kind='PAYE', rate_percent=Decimal('10'), effective_from=date(2026, 1, 1))
        PayrollAdjustment.objects.create(company=self.company, employee=self.employee, kind='LATENESS', name='Lateness', amount=Decimal('1000'), month=date(2026, 7, 1), reason='Three late arrivals recorded.', status='APPROVED')
        run = PayrollService.calculate(self.run, self.hr)
        item = run.items.get()
        self.assertEqual(item.gross_pay, Decimal('100000.00'))
        self.assertEqual(item.total_deductions, Decimal('11000.00'))
        self.assertEqual(item.net_pay, Decimal('89000.00'))

    def test_deductions_are_capped_boundary(self):
        PayrollConfig.objects.filter(company=self.company).update(maximum_deduction_percent=Decimal('25'))
        PayrollAdjustment.objects.create(company=self.company, employee=self.employee, kind='CUSTOM', name='Fine', amount=Decimal('90000'), month=date(2026, 7, 1), reason='Documented policy deduction.', status='APPROVED')
        run = PayrollService.calculate(self.run, self.hr)
        self.assertEqual(run.items.get().total_deductions, Decimal('25000.00'))

    def test_missing_bank_details_and_self_approval_are_rejected_error(self):
        self.profile.bank_code = ''; self.profile.save()
        with self.assertRaises(ValidationError):
            PayrollService.calculate(self.run, self.hr)
        self.profile.bank_code = '058'; self.profile.save()
        PayrollService.calculate(self.run, self.hr)
        with self.assertRaises(ValidationError):
            PayrollService.review_or_approve(self.run, self.hr)

    def test_finance_exports_settlement_pack_and_reconciles_happy_path(self):
        PayrollService.calculate(self.run, self.hr)
        PayrollService.review_or_approve(self.run, self.finance)
        PayrollService.review_or_approve(self.run, self.finance, approve=True)
        paths = PayrollService.export(self.run, self.finance, 'PACK')
        self.assertEqual({path.suffix for path in paths}, {'.csv', '.xlsx', '.pdf'})
        self.assertTrue(all(Path(path).exists() for path in paths))
        self.run.refresh_from_db()
        PayrollService.reconcile(self.run, self.finance, 'INF-001', 'SUCCESS', {'matched': 1})
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, 'RECONCILED')

    def test_employee_contests_and_finance_removes_deduction_happy_path(self):
        adjustment = PayrollAdjustment.objects.create(company=self.company, employee=self.employee, kind='CUSTOM', name='Disputed fine', amount=Decimal('5000'), month=date(2026, 7, 1), reason='Documented policy deduction.', status='APPROVED')
        PayrollService.calculate(self.run, self.hr)
        deduction = self.run.items.get().deductions.get(adjustment=adjustment)
        PayrollService.contest_deduction(deduction, self.employee, 'The incident did not involve me.')
        deduction.refresh_from_db()
        self.assertTrue(deduction.is_held)
        PayrollService.resolve_deduction(deduction, self.finance, uphold=False, notes='Evidence confirms employee dispute.')
        deduction.refresh_from_db()
        self.assertEqual(deduction.amount, Decimal('0.00'))

    def test_other_employee_cannot_contest_deduction_error(self):
        other = Employee.objects.create_user(username='other_employee', password='x', company=self.company)
        adjustment = PayrollAdjustment.objects.create(company=self.company, employee=self.employee, kind='CUSTOM', name='Fine', amount=Decimal('5000'), month=date(2026, 7, 1), reason='Documented policy deduction.', status='APPROVED')
        PayrollService.calculate(self.run, self.hr)
        with self.assertRaises(ValidationError):
            PayrollService.contest_deduction(self.run.items.get().deductions.get(adjustment=adjustment), other, 'This is not mine.')

    def test_csv_row_validation_reports_invalid_rows(self):
        payroll_csv = io.StringIO(
            'employee_number,base_salary,bank_code,hire_date\n'
            'E001,100000.00,058,2025-01-01\n'
            'BAD,0,abc,2025-01-01\n'
        )
        valid_rows, errors = PayrollImportService.validate_profile_csv(self.company, payroll_csv)
        self.assertEqual(len(valid_rows), 1)
        self.assertEqual(len(errors), 1)
        self.assertIn('base_salary', errors[0]['issues'])
        self.assertIn('bank_code', errors[0]['issues'])

    def test_import_profiles_updates_existing_company_profiles(self):
        payroll_csv = io.StringIO(
            'employee_number,base_salary,bank_code,hire_date\n'
            'E001,95000.00,001,2025-02-01\n'
        )
        imported = PayrollImportService.import_profiles(self.company, payroll_csv)
        self.profile.refresh_from_db()
        self.assertEqual(imported, 1)
        self.assertEqual(self.profile.base_salary, Decimal('95000.00'))
        self.assertEqual(self.profile.bank_code, '001')
        self.assertEqual(self.profile.hire_date, date(2025, 2, 1))

    def test_cross_company_finance_user_cannot_reconcile_exports(self):
        other_company = Company.objects.create(name='Other Co')
        foreign_finance = Employee.objects.create_user(username='foreign_finance', password='x', company=other_company, role=EmployeeRole.FINANCE)
        PayrollService.calculate(self.run, self.hr)
        PayrollService.review_or_approve(self.run, self.finance)
        PayrollService.review_or_approve(self.run, self.finance, approve=True)
        PayrollService.export(self.run, self.finance, 'CSV')
        self.run.refresh_from_db()

        with self.assertRaises(ValidationError):
            PayrollService.reconcile(self.run, foreign_finance, 'INF-001', 'SUCCESS', {'matched': 1})

    def test_cross_company_employee_cannot_contest_deduction(self):
        other_company = Company.objects.create(name='Other Co')
        foreign_employee = Employee.objects.create_user(username='foreign_employee', password='x', company=other_company)
        adjustment = PayrollAdjustment.objects.create(company=self.company, employee=self.employee, kind='CUSTOM', name='Fine', amount=Decimal('5000'), month=date(2026, 7, 1), reason='Documented policy deduction.', status='APPROVED')
        PayrollService.calculate(self.run, self.hr)
        deduction = self.run.items.get().deductions.get(adjustment=adjustment)

        with self.assertRaises(ValidationError):
            PayrollService.contest_deduction(deduction, foreign_employee, 'This is not mine.')
