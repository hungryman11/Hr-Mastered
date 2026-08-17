from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from core.loan import LoanComplianceService
from core.models import Company, Employee, EmployeeRole, LoanCase, LoanCaseChecklistItem, LoanChecklistTemplateItem, LoanProduct


class LoanComplianceApiTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Loan Co')
        self.hr = Employee.objects.create_user(
            username='loan_hr', email='hr@loan.co', password='password123', company=self.company, role=EmployeeRole.HR_ADMIN,
        )
        self.risk_checker = Employee.objects.create_user(
            username='loan_checker', email='checker@loan.co', password='password123', company=self.company, role=EmployeeRole.RISK_CHECKER,
        )
        self.compliance_admin = Employee.objects.create_user(
            username='loan_admin', email='admin@loan.co', password='password123', company=self.company, role=EmployeeRole.COMPLIANCE_ADMIN,
        )
        self.applicant = Employee.objects.create_user(
            username='loan_applicant', email='applicant@loan.co', password='password123', company=self.company, role=EmployeeRole.EMPLOYEE,
        )
        self.product = LoanProduct.objects.create(company=self.company, name='Quick Advance', created_by=self.hr, updated_by=self.hr)
        LoanChecklistTemplateItem.objects.create(company=self.company, loan_product=self.product, name='Bank statement', required=True, sort_order=1, created_by=self.hr, updated_by=self.hr)
        LoanChecklistTemplateItem.objects.create(company=self.company, loan_product=self.product, name='Utility bill', required=False, sort_order=2, created_by=self.hr, updated_by=self.hr)
        self.client = APIClient()
        self.client.force_authenticate(user=self.hr)

    def test_loan_case_service_copies_checklist_snapshot_and_immutable_audit(self):
        case = LoanComplianceService.create_case(
            company=self.company,
            applicant=self.applicant,
            product=self.product,
            amount=Decimal('25000.00'),
            purpose='Working capital',
            repayment_months=12,
            collateral_type='Vehicle',
            collateral_value=Decimal('40000.00'),
            collateral_details='Blue sedan',
            actor=self.hr,
        )

        self.assertEqual(case.checklist_items.count(), 2)
        self.assertEqual(case.checklist_items.filter(name='Bank statement').count(), 1)
        self.assertEqual(case.audit_events.count(), 1)
        self.assertEqual(case.status, LoanCase.Status.IN_REVIEW)

    def test_loan_product_api_is_exposed_for_company_members(self):
        response = self.client.get('/api/loan-products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cross_company_compliance_admin_cannot_decide_case(self):
        other_company = Company.objects.create(name='Other Loan Co')
        foreign_admin = Employee.objects.create_user(
            username='foreign_admin', email='foreign@loan.co', password='password123', company=other_company, role=EmployeeRole.COMPLIANCE_ADMIN,
        )
        case = LoanComplianceService.create_case(
            company=self.company,
            applicant=self.applicant,
            product=self.product,
            amount=Decimal('25000.00'),
            purpose='Working capital',
            repayment_months=12,
            collateral_type='Vehicle',
            collateral_value=Decimal('40000.00'),
            collateral_details='Blue sedan',
            actor=self.hr,
        )

        with self.assertRaises(ValidationError):
            LoanComplianceService.decide(case, foreign_admin, LoanCase.Status.APPROVED, 'This admin is not from the same company.')

    def test_invalid_checklist_status_is_rejected(self):
        case = LoanComplianceService.create_case(
            company=self.company,
            applicant=self.applicant,
            product=self.product,
            amount=Decimal('25000.00'),
            purpose='Working capital',
            repayment_months=12,
            collateral_type='Vehicle',
            collateral_value=Decimal('40000.00'),
            collateral_details='Blue sedan',
            actor=self.hr,
        )
        item = case.checklist_items.get(name='Bank statement')

        with self.assertRaises(Exception):
            LoanComplianceService.check_item(
                item=item,
                checker=self.risk_checker,
                status='UNKNOWN',
                note='Unsupported state',
                evidence_reference='REF-001',
            )
