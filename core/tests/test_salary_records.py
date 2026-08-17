from decimal import Decimal
from datetime import date
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Company, Employee, EmployeeRole, SalaryRecord,
)


@override_settings(ZOHO_USE_MOCK=True)
class SalaryRecordTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Paycraft Ltd')
        self.other_company = Company.objects.create(name='Other Corp')

        self.hr = Employee.objects.create_user(
            username='hr_salary', email='hr@paycraft.com', password='password123',
            company=self.company, role=EmployeeRole.HR_ADMIN,
        )
        self.manager = Employee.objects.create_user(
            username='mgr_salary', email='mgr@paycraft.com', password='password123',
            company=self.company, role=EmployeeRole.MANAGER,
        )
        self.employee1 = Employee.objects.create_user(
            username='emp_alice', email='alice@paycraft.com', password='password123',
            company=self.company, role=EmployeeRole.EMPLOYEE, manager=self.manager,
        )
        self.employee2 = Employee.objects.create_user(
            username='emp_bob', email='bob@paycraft.com', password='password123',
            company=self.company, role=EmployeeRole.EMPLOYEE,
        )
        self.other_emp = Employee.objects.create_user(
            username='other_emp', email='other@other.com', password='password123',
            company=self.other_company, role=EmployeeRole.EMPLOYEE,
        )

        self.client = APIClient()

    # ------------------------------------------------------------------ #
    # Model-level tests                                                    #
    # ------------------------------------------------------------------ #

    def test_gross_salary_computed_property(self):
        """gross_salary = sum of all allowance components."""
        record = SalaryRecord(
            company=self.company,
            employee=self.employee1,
            effective_date=date(2026, 1, 1),
            base_salary=Decimal('500000.00'),
            housing_allowance=Decimal('100000.00'),
            transport_allowance=Decimal('50000.00'),
            meal_allowance=Decimal('30000.00'),
            other_allowances=Decimal('20000.00'),
        )
        self.assertEqual(record.gross_salary, Decimal('700000.00'))

    def test_end_date_must_be_after_effective_date(self):
        """end_date <= effective_date must raise ValidationError."""
        record = SalaryRecord(
            company=self.company,
            employee=self.employee1,
            effective_date=date(2026, 6, 1),
            end_date=date(2026, 5, 31),
            base_salary=Decimal('500000.00'),
        )
        with self.assertRaises(ValidationError):
            record.save()

    def test_overlap_prevention_open_ended_records(self):
        """
        Creating a second ACTIVE open-ended record for the same employee
        must raise ValidationError due to infinite overlap.
        """
        SalaryRecord.objects.create(
            company=self.company,
            employee=self.employee1,
            effective_date=date(2026, 1, 1),
            base_salary=Decimal('500000.00'),
            status=SalaryRecord.Status.ACTIVE,
        )
        duplicate = SalaryRecord(
            company=self.company,
            employee=self.employee1,
            effective_date=date(2026, 6, 1),
            base_salary=Decimal('600000.00'),
            status=SalaryRecord.Status.ACTIVE,
        )
        with self.assertRaises(ValidationError):
            duplicate.save()

    def test_overlap_prevention_bounded_ranges(self):
        """Overlapping bounded date ranges must be rejected."""
        SalaryRecord.objects.create(
            company=self.company,
            employee=self.employee1,
            effective_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
            base_salary=Decimal('500000.00'),
            status=SalaryRecord.Status.ACTIVE,
        )
        overlapping = SalaryRecord(
            company=self.company,
            employee=self.employee1,
            effective_date=date(2026, 4, 1),
            end_date=date(2026, 9, 30),
            base_salary=Decimal('550000.00'),
            status=SalaryRecord.Status.ACTIVE,
        )
        with self.assertRaises(ValidationError):
            overlapping.save()

    def test_superseded_status_does_not_trigger_overlap(self):
        """SUPERSEDED records do not count for overlap validation."""
        SalaryRecord.objects.create(
            company=self.company,
            employee=self.employee1,
            effective_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            base_salary=Decimal('400000.00'),
            status=SalaryRecord.Status.SUPERSEDED,
        )
        # Should not raise — different status
        new_record = SalaryRecord(
            company=self.company,
            employee=self.employee1,
            effective_date=date(2025, 6, 1),
            end_date=date(2025, 9, 30),
            base_salary=Decimal('500000.00'),
            status=SalaryRecord.Status.ACTIVE,
        )
        new_record.save()  # No exception expected
        self.assertIsNotNone(new_record.pk)

    def test_salary_records_are_company_isolated(self):
        """A salary record for an employee of a different company must raise ValidationError."""
        record = SalaryRecord(
            company=self.company,
            employee=self.other_emp,  # Cross-company employee
            effective_date=date(2026, 1, 1),
            base_salary=Decimal('300000.00'),
        )
        with self.assertRaises(ValidationError):
            record.save()

    # ------------------------------------------------------------------ #
    # API tests: HR write access                                           #
    # ------------------------------------------------------------------ #

    def test_hr_can_create_salary_record(self):
        self.client.force_authenticate(user=self.hr)
        resp = self.client.post('/api/salary-records/', {
            'employee': self.employee1.pk,
            'effective_date': '2026-01-01',
            'base_salary': '500000.00',
            'housing_allowance': '100000.00',
            'transport_allowance': '50000.00',
            'meal_allowance': '30000.00',
            'other_allowances': '0.00',
            'currency': 'NGN',
            'reason': 'Initial onboarding salary',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['gross_salary'], '680000.00')
        self.assertEqual(resp.data['status'], 'ACTIVE')

    def test_employee_cannot_create_salary_record(self):
        self.client.force_authenticate(user=self.employee1)
        resp = self.client.post('/api/salary-records/', {
            'employee': self.employee1.pk,
            'effective_date': '2026-01-01',
            'base_salary': '999999.00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_cannot_create_salary_record(self):
        self.client.force_authenticate(user=self.manager)
        resp = self.client.post('/api/salary-records/', {
            'employee': self.employee1.pk,
            'effective_date': '2026-01-01',
            'base_salary': '500000.00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ------------------------------------------------------------------ #
    # API tests: Employee read-only scoping                                #
    # ------------------------------------------------------------------ #

    def test_employee_sees_only_own_salary_records(self):
        """Employees cannot see peer salary records."""
        SalaryRecord.objects.create(
            company=self.company, employee=self.employee1,
            effective_date=date(2026, 1, 1), base_salary=Decimal('500000.00'),
        )
        SalaryRecord.objects.create(
            company=self.company, employee=self.employee2,
            effective_date=date(2026, 1, 1), base_salary=Decimal('450000.00'),
        )
        self.client.force_authenticate(user=self.employee1)
        resp = self.client.get('/api/salary-records/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        records = list(resp.data)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['employee'], self.employee1.pk)

    def test_employee_ledger_defaults_to_current_salary_only(self):
        SalaryRecord.objects.create(
            company=self.company, employee=self.employee1,
            effective_date=date(2025, 1, 1), end_date=date(2025, 12, 31),
            base_salary=Decimal('400000.00'), status=SalaryRecord.Status.SUPERSEDED,
        )
        current = SalaryRecord.objects.create(
            company=self.company, employee=self.employee1,
            effective_date=date(2026, 1, 1), base_salary=Decimal('500000.00'),
            status=SalaryRecord.Status.ACTIVE,
        )
        self.client.force_authenticate(user=self.employee1)
        response = self.client.get('/api/salary-records/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row['uuid'] for row in response.data], [str(current.uuid)])

    def test_hr_can_see_all_company_salary_records(self):
        """HR admins see all records for their company."""
        SalaryRecord.objects.create(
            company=self.company, employee=self.employee1,
            effective_date=date(2026, 1, 1), base_salary=Decimal('500000.00'),
        )
        SalaryRecord.objects.create(
            company=self.company, employee=self.employee2,
            effective_date=date(2026, 1, 1), base_salary=Decimal('450000.00'),
        )
        self.client.force_authenticate(user=self.hr)
        resp = self.client.get('/api/salary-records/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        records = list(resp.data)
        self.assertGreaterEqual(len(records), 2)

    def test_cross_company_isolation_via_api(self):
        """Other-company employee cannot see this company's records."""
        SalaryRecord.objects.create(
            company=self.company, employee=self.employee1,
            effective_date=date(2026, 1, 1), base_salary=Decimal('500000.00'),
        )
        self.client.force_authenticate(user=self.other_emp)
        resp = self.client.get('/api/salary-records/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        records = list(resp.data)
        self.assertEqual(len(records), 0)

    # ------------------------------------------------------------------ #
    # API tests: Supersede action                                          #
    # ------------------------------------------------------------------ #

    def test_supersede_action_transitions_and_creates_new_record(self):
        """
        POST /api/salary-records/supersede/ should:
        1. Mark existing ACTIVE record as SUPERSEDED with end_date = new_effective - 1d.
        2. Create a new ACTIVE salary record.
        """
        SalaryRecord.objects.create(
            company=self.company, employee=self.employee1,
            effective_date=date(2026, 1, 1), base_salary=Decimal('500000.00'),
            status=SalaryRecord.Status.ACTIVE,
        )
        self.client.force_authenticate(user=self.hr)
        resp = self.client.post('/api/salary-records/supersede/', {
            'employee_uuid': str(self.employee1.uuid),
            'effective_date': '2026-07-01',
            'base_salary': '600000.00',
            'housing_allowance': '120000.00',
            'transport_allowance': '60000.00',
            'meal_allowance': '0.00',
            'other_allowances': '0.00',
            'currency': 'NGN',
            'reason': 'Mid-year promotion',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['gross_salary'], '780000.00')

        # Old record should now be SUPERSEDED
        old = SalaryRecord.all_objects.filter(
            company=self.company, employee=self.employee1,
            status=SalaryRecord.Status.SUPERSEDED,
        ).first()
        self.assertIsNotNone(old)
        self.assertEqual(str(old.end_date), '2026-06-30')

    # ------------------------------------------------------------------ #
    # API tests: Current salary lookup                                     #
    # ------------------------------------------------------------------ #

    def test_current_salary_endpoint_returns_active_record(self):
        SalaryRecord.objects.create(
            company=self.company, employee=self.employee1,
            effective_date=date(2026, 1, 1), base_salary=Decimal('500000.00'),
            status=SalaryRecord.Status.ACTIVE,
        )
        self.client.force_authenticate(user=self.employee1)
        resp = self.client.get('/api/salary-records/current/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['base_salary'], '500000.00')

    def test_hr_can_lookup_any_employee_current_salary(self):
        SalaryRecord.objects.create(
            company=self.company, employee=self.employee2,
            effective_date=date(2026, 1, 1), base_salary=Decimal('450000.00'),
            status=SalaryRecord.Status.ACTIVE,
        )
        self.client.force_authenticate(user=self.hr)
        resp = self.client.get(f'/api/salary-records/current/?employee_uuid={self.employee2.uuid}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['base_salary'], '450000.00')

    def test_employee_cannot_lookup_peer_current_salary(self):
        SalaryRecord.objects.create(
            company=self.company, employee=self.employee2,
            effective_date=date(2026, 1, 1), base_salary=Decimal('450000.00'),
            status=SalaryRecord.Status.ACTIVE,
        )
        self.client.force_authenticate(user=self.employee1)
        resp = self.client.get(f'/api/salary-records/current/?employee_uuid={self.employee2.uuid}')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
