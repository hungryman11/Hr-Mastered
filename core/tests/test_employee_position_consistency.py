from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Company, Employee, EmployeeRole, OrgUnit, Position


@override_settings(ZOHO_USE_MOCK=True)
class EmployeePositionOrgUnitConsistencyTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Infinity Corp')
        self.other_company = Company.objects.create(name='Other Corp')

        self.org_unit_ops = OrgUnit.objects.create(
            company=self.company, name='Operations', unit_type=OrgUnit.UnitType.DEPARTMENT
        )
        self.org_unit_credit = OrgUnit.objects.create(
            company=self.company, name='Credit & Marketing', unit_type=OrgUnit.UnitType.DEPARTMENT
        )
        self.other_org_unit = OrgUnit.objects.create(
            company=self.other_company, name='External Ops', unit_type=OrgUnit.UnitType.DEPARTMENT
        )

        self.pos_ops = Position.objects.create(
            company=self.company, title='Operations Lead', org_unit=self.org_unit_ops
        )
        self.pos_credit = Position.objects.create(
            company=self.company, title='Credit Analyst', org_unit=self.org_unit_credit
        )
        self.pos_generic = Position.objects.create(
            company=self.company, title='General Staff', org_unit=None
        )
        self.other_pos = Position.objects.create(
            company=self.other_company, title='External Position', org_unit=self.other_org_unit
        )

        self.hr_admin = Employee.objects.create_user(
            username='hr_admin_user', email='hr@infinity.com', password='password123',
            company=self.company, role=EmployeeRole.HR_ADMIN, is_org_admin=True,
        )

        self.client = APIClient()

    # ------------------------------------------------------------------ #
    # 1. Valid employee + matching position/org unit succeeds             #
    # ------------------------------------------------------------------ #
    def test_valid_employee_matching_position_and_org_unit_model_save(self):
        """Employee with org_unit matching position.org_unit saves successfully."""
        emp = Employee(
            username='valid_emp',
            email='valid@infinity.com',
            company=self.company,
            org_unit=self.org_unit_ops,
            position=self.pos_ops,
            role=EmployeeRole.EMPLOYEE,
        )
        emp.set_password('password123')
        emp.save()
        self.assertIsNotNone(emp.pk)
        self.assertEqual(emp.org_unit, self.pos_ops.org_unit)

    # ------------------------------------------------------------------ #
    # 2. Invalid employee + mismatching position/org unit fails           #
    # ------------------------------------------------------------------ #
    def test_invalid_employee_mismatching_position_and_org_unit_model_fails(self):
        """Employee with org_unit != position.org_unit raises ValidationError on save."""
        emp = Employee(
            username='mismatch_emp',
            email='mismatch@infinity.com',
            company=self.company,
            org_unit=self.org_unit_ops,  # Operations
            position=self.pos_credit,    # Credit & Marketing
            role=EmployeeRole.EMPLOYEE,
        )
        emp.set_password('password123')
        with self.assertRaises(ValidationError) as ctx:
            emp.save()
        self.assertIn('org_unit', ctx.exception.message_dict)

    # ------------------------------------------------------------------ #
    # 3. Employee update changing org_unit to conflict with position fails#
    # ------------------------------------------------------------------ #
    def test_update_changing_org_unit_to_conflict_fails(self):
        """Updating org_unit to one that conflicts with existing position raises ValidationError."""
        emp = Employee.objects.create_user(
            username='update_emp_1',
            email='update1@infinity.com',
            password='password123',
            company=self.company,
            org_unit=self.org_unit_ops,
            position=self.pos_ops,
            role=EmployeeRole.EMPLOYEE,
        )
        emp.org_unit = self.org_unit_credit
        with self.assertRaises(ValidationError) as ctx:
            emp.save()
        self.assertIn('org_unit', ctx.exception.message_dict)

    # ------------------------------------------------------------------ #
    # 4. Employee update changing position to conflict with org_unit fails#
    # ------------------------------------------------------------------ #
    def test_update_changing_position_to_conflict_fails(self):
        """Updating position to one that conflicts with employee org_unit raises ValidationError."""
        emp = Employee.objects.create_user(
            username='update_emp_2',
            email='update2@infinity.com',
            password='password123',
            company=self.company,
            org_unit=self.org_unit_ops,
            position=self.pos_ops,
            role=EmployeeRole.EMPLOYEE,
        )
        emp.position = self.pos_credit
        with self.assertRaises(ValidationError) as ctx:
            emp.save()
        self.assertIn('org_unit', ctx.exception.message_dict)

    # ------------------------------------------------------------------ #
    # 5. Position without org_unit remains valid where allowed            #
    # ------------------------------------------------------------------ #
    def test_position_without_org_unit_is_valid(self):
        """A generic position without an org_unit can be assigned with any or no org_unit."""
        emp1 = Employee.objects.create_user(
            username='generic_pos_emp1',
            email='gen1@infinity.com',
            password='password123',
            company=self.company,
            org_unit=self.org_unit_ops,
            position=self.pos_generic,
            role=EmployeeRole.EMPLOYEE,
        )
        self.assertIsNotNone(emp1.pk)

        emp2 = Employee.objects.create_user(
            username='generic_pos_emp2',
            email='gen2@infinity.com',
            password='password123',
            company=self.company,
            org_unit=None,
            position=self.pos_generic,
            role=EmployeeRole.EMPLOYEE,
        )
        self.assertIsNotNone(emp2.pk)

    # ------------------------------------------------------------------ #
    # 6. Cross-company position remains rejected                         #
    # ------------------------------------------------------------------ #
    def test_cross_company_position_rejected_at_model_level(self):
        """Assigning a Position from another company raises ValidationError."""
        emp = Employee(
            username='cross_pos_emp',
            email='cross@infinity.com',
            company=self.company,
            position=self.other_pos,
            role=EmployeeRole.EMPLOYEE,
        )
        emp.set_password('password123')
        with self.assertRaises(ValidationError) as ctx:
            emp.save()
        self.assertIn('position', ctx.exception.message_dict)

    # ------------------------------------------------------------------ #
    # 7. API-level serializer validation tests                            #
    # ------------------------------------------------------------------ #
    def test_api_create_employee_with_mismatching_position_and_org_unit_fails(self):
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.post('/api/employees/', {
            'username': 'api_mismatch_user',
            'email': 'api_mismatch@infinity.com',
            'first_name': 'Test',
            'last_name': 'User',
            'org_unit': self.org_unit_ops.pk,
            'position': self.pos_credit.pk,
            'role': 'EMPLOYEE',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('org_unit', resp.data)

    def test_api_create_employee_with_matching_position_and_org_unit_succeeds(self):
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.post('/api/employees/', {
            'username': 'api_valid_user',
            'email': 'api_valid@infinity.com',
            'first_name': 'Valid',
            'last_name': 'User',
            'org_unit': self.org_unit_ops.pk,
            'position': self.pos_ops.pk,
            'role': 'EMPLOYEE',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_api_patch_employee_to_mismatching_position_fails(self):
        emp = Employee.objects.create_user(
            username='api_patch_user',
            email='patch@infinity.com',
            password='password123',
            company=self.company,
            org_unit=self.org_unit_ops,
            position=self.pos_ops,
            role=EmployeeRole.EMPLOYEE,
        )
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.patch(f'/api/employees/{emp.uuid}/', {
            'position': self.pos_credit.pk,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('org_unit', resp.data)

    # ------------------------------------------------------------------ #
    # 8. Obsolete loan roles cannot be assigned                          #
    # ------------------------------------------------------------------ #
    def test_obsolete_loan_roles_rejected_by_api(self):
        """Assigning RISK_CHECKER or COMPLIANCE_ADMIN returns 400 Bad Request."""
        self.client.force_authenticate(user=self.hr_admin)
        for obsolete_role in ['RISK_CHECKER', 'COMPLIANCE_ADMIN']:
            resp = self.client.post('/api/employees/', {
                'username': f'user_{obsolete_role.lower()}',
                'email': f'{obsolete_role.lower()}@infinity.com',
                'first_name': 'Obs',
                'last_name': 'Role',
                'role': obsolete_role,
            }, format='json')
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('role', resp.data)
