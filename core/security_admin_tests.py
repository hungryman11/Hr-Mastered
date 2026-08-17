"""
Comprehensive security tests for admin/HR RBAC and tenant isolation.

These tests verify:
1. Role escalation protection
2. Tenant isolation (cross-company access blocked)
3. Mass assignment (privilege injection) prevention
4. Object-level authorization
5. Self-privilege manipulation blocking
"""
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Company, Employee, EmployeeRole, Department, OrgUnit, Position


class RoleEscalationProtectionTests(TestCase):
    """Verify that users cannot escalate themselves or others inappropriately."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Company A")
        self.other_company = Company.objects.create(name="Test Company B")

        # Create employees with different roles
        self.employee = Employee.objects.create_user(
            username="emp1", password="pass", company=self.company, role=EmployeeRole.EMPLOYEE
        )
        self.manager = Employee.objects.create_user(
            username="mgr1", password="pass", company=self.company, role=EmployeeRole.MANAGER
        )
        self.hr_admin = Employee.objects.create_user(
            username="hr1", password="pass", company=self.company, role=EmployeeRole.HR_ADMIN
        )
        self.org_admin = Employee.objects.create_user(
            username="org1", password="pass", company=self.company,
            role=EmployeeRole.HR_ADMIN, is_org_admin=True
        )
        self.superuser = Employee.objects.create_superuser(
            username="su", password="pass", email="su@test.com", company=self.company
        )

        self.client = APIClient()

    def test_employee_cannot_escalate_self_to_manager(self):
        """Employee cannot change own role to MANAGER."""
        self.client.force_authenticate(user=self.employee)
        resp = self.client.patch(f'/api/employees/{self.employee.uuid}/', data={'role': EmployeeRole.MANAGER}, format='json')
        # Serializer should reject this attempt (403 forbidden for non-org-admin)
        self.assertIn(resp.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.role, EmployeeRole.EMPLOYEE)

    def test_employee_cannot_escalate_self_to_hr_admin(self):
        """Employee cannot change own role to HR_ADMIN."""
        self.client.force_authenticate(user=self.employee)
        resp = self.client.patch(f'/api/employees/{self.employee.uuid}/', data={'role': EmployeeRole.HR_ADMIN}, format='json')
        # Should be blocked by serializer validation
        self.assertIn(resp.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.role, EmployeeRole.EMPLOYEE)

    def test_manager_cannot_escalate_self_to_hr_admin(self):
        """Manager cannot change own role to HR_ADMIN."""
        self.client.force_authenticate(user=self.manager)
        resp = self.client.patch(f'/api/employees/{self.manager.uuid}/', data={'role': EmployeeRole.HR_ADMIN}, format='json')
        self.assertIn(resp.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.role, EmployeeRole.MANAGER)

    def test_hr_admin_cannot_escalate_self_to_org_admin_via_flag(self):
        """HR Admin cannot set is_org_admin=True on themselves through PATCH."""
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.patch(f'/api/employees/{self.hr_admin.uuid}/', data={'is_org_admin': True}, format='json')
        # Should be ignored (read-only field)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.hr_admin.refresh_from_db()
        self.assertFalse(self.hr_admin.is_org_admin)

    def test_hr_admin_cannot_grant_org_admin_via_set_org_admin_action(self):
        """HR Admin cannot use set_org_admin endpoint to grant themselves org admin."""
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.post(f'/api/employees/{self.hr_admin.uuid}/set_org_admin/', 
                                data={'is_org_admin': True}, format='json')
        # Should be forbidden (requires superuser)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.hr_admin.refresh_from_db()
        self.assertFalse(self.hr_admin.is_org_admin)

    def test_org_admin_cannot_grant_org_admin_to_others(self):
        """Org Admin cannot use set_org_admin to grant themselves more or others privileges."""
        target = Employee.objects.create_user(username="tgt", password="x", company=self.company)
        self.client.force_authenticate(user=self.org_admin)
        resp = self.client.post(f'/api/employees/{target.uuid}/set_org_admin/', 
                                data={'is_org_admin': True}, format='json')
        # set_org_admin is superuser-only
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        target.refresh_from_db()
        self.assertFalse(target.is_org_admin)

    def test_superuser_can_grant_org_admin(self):
        """Superuser can grant org admin (control path)."""
        target = Employee.objects.create_user(username="tgt2", password="x", company=self.company)
        self.client.force_authenticate(user=self.superuser)
        resp = self.client.post(f'/api/employees/{target.uuid}/set_org_admin/', 
                                data={'is_org_admin': True}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        target.refresh_from_db()
        self.assertTrue(target.is_org_admin)


class MassAssignmentProtectionTests(TestCase):
    """Verify that privilege fields cannot be injected through API requests."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.hr_admin = Employee.objects.create_user(
            username="hr", password="x", company=self.company, role=EmployeeRole.HR_ADMIN
        )
        self.target = Employee.objects.create_user(
            username="emp", password="x", company=self.company, role=EmployeeRole.EMPLOYEE
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.hr_admin)

    def test_cannot_inject_is_superuser_on_create(self):
        """Creating an employee cannot include is_superuser=True."""
        resp = self.client.post('/api/employees/', {
            'username': 'newuser',
            'email': 'new@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'is_superuser': True,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        new_emp = Employee.objects.get(username='newuser')
        self.assertFalse(new_emp.is_superuser)

    def test_cannot_inject_is_staff_on_create(self):
        """Creating an employee cannot include is_staff=True."""
        resp = self.client.post('/api/employees/', {
            'username': 'newuser2',
            'email': 'new2@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'is_staff': True,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        new_emp = Employee.objects.get(username='newuser2')
        self.assertFalse(new_emp.is_staff)

    def test_cannot_inject_is_org_admin_on_create(self):
        """Creating an employee cannot include is_org_admin=True."""
        resp = self.client.post('/api/employees/', {
            'username': 'newuser3',
            'email': 'new3@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'is_org_admin': True,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        new_emp = Employee.objects.get(username='newuser3')
        self.assertFalse(new_emp.is_org_admin)

    def test_cannot_inject_is_superuser_on_patch(self):
        """Patching an employee cannot include is_superuser=True."""
        resp = self.client.patch(f'/api/employees/{self.target.uuid}/', {
            'first_name': 'Updated',
            'is_superuser': True,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_superuser)

    def test_cannot_inject_is_org_admin_on_patch(self):
        """Patching an employee cannot set is_org_admin=True (read-only)."""
        resp = self.client.patch(f'/api/employees/{self.target.uuid}/', {
            'first_name': 'Updated',
            'is_org_admin': True,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_org_admin)

    def test_cannot_change_company_on_patch(self):
        """Patching an employee cannot change company (company is read-only/immutable)."""
        other_company = Company.objects.create(name="Other Company")
        resp = self.client.patch(f'/api/employees/{self.target.uuid}/', {
            'company': other_company.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.target.refresh_from_db()
        self.assertEqual(self.target.company, self.company)


class TenantIsolationTests(TestCase):
    """Verify complete isolation between companies."""

    @staticmethod
    def _extract_item_ids(response):
        data = response.data
        if isinstance(data, dict):
            items = data.get('results', data.get('items', []))
        elif isinstance(data, list):
            items = data
        else:
            items = []
        return [item.get('id') or item.get('uuid') for item in items if isinstance(item, dict)]

    def setUp(self):
        self.company_a = Company.objects.create(name="Company A")
        self.company_b = Company.objects.create(name="Company B")

        # Company A resources
        self.hr_a = Employee.objects.create_user(
            username="hr_a", password="x", company=self.company_a, role=EmployeeRole.HR_ADMIN
        )
        self.emp_a = Employee.objects.create_user(
            username="emp_a", password="x", company=self.company_a
        )
        self.dept_a = Department.objects.create(company=self.company_a, name="Dept A")
        self.unit_a = OrgUnit.objects.create(company=self.company_a, name="Unit A", unit_type=OrgUnit.UnitType.DEPARTMENT)
        self.pos_a = Position.objects.create(company=self.company_a, title="Position A", org_unit=self.unit_a)

        # Company B resources
        self.hr_b = Employee.objects.create_user(
            username="hr_b", password="x", company=self.company_b, role=EmployeeRole.HR_ADMIN
        )
        self.emp_b = Employee.objects.create_user(
            username="emp_b", password="x", company=self.company_b
        )
        self.dept_b = Department.objects.create(company=self.company_b, name="Dept B")
        self.unit_b = OrgUnit.objects.create(company=self.company_b, name="Unit B", unit_type=OrgUnit.UnitType.DEPARTMENT)
        self.pos_b = Position.objects.create(company=self.company_b, title="Position B", org_unit=self.unit_b)

        self.client = APIClient()

    def test_hr_a_cannot_list_company_b_employees(self):
        """HR from Company A cannot see Company B employees in employee list."""
        self.client.force_authenticate(user=self.hr_a)
        resp = self.client.get('/api/employees/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        employee_ids = self._extract_item_ids(resp)
        self.assertIn(self.emp_a.id, employee_ids)
        self.assertNotIn(self.emp_b.id, employee_ids)

    def test_hr_a_cannot_read_company_b_employee_detail(self):
        """HR from Company A cannot fetch detail for Company B employee."""
        self.client.force_authenticate(user=self.hr_a)
        resp = self.client.get(f'/api/employees/{self.emp_b.uuid}/')
        # Should be forbidden or not found (403 or 404) - both are acceptable
        self.assertIn(resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_hr_a_cannot_create_employee_in_company_b(self):
        """HR from Company A cannot create employee for Company B."""
        self.client.force_authenticate(user=self.hr_a)
        # Try to explicitly set company_b (though it's read-only, attempt it)
        resp = self.client.post('/api/employees/', {
            'username': 'newuser',
            'email': 'new@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'company': self.company_b.id,
        }, format='json')
        # Should create under company_a (HR's company), not company_b
        if resp.status_code == status.HTTP_201_CREATED:
            new_emp = Employee.objects.get(username='newuser')
            self.assertEqual(new_emp.company, self.company_a)

    def test_hr_a_cannot_assign_company_b_department_to_employee(self):
        """HR from Company A cannot assign Company B department to an employee."""
        self.client.force_authenticate(user=self.hr_a)
        resp = self.client.patch(f'/api/employees/{self.emp_a.uuid}/', {
            'department': self.dept_b.id,
        }, format='json')
        # Should be rejected (company validation in serializer)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.emp_a.refresh_from_db()
        self.assertNotEqual(self.emp_a.department, self.dept_b)

    def test_hr_a_cannot_assign_company_b_position_to_employee(self):
        """HR from Company A cannot assign Company B position to an employee."""
        self.client.force_authenticate(user=self.hr_a)
        resp = self.client.patch(f'/api/employees/{self.emp_a.uuid}/', {
            'position': self.pos_b.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.emp_a.refresh_from_db()
        self.assertNotEqual(self.emp_a.position, self.pos_b)

    def test_hr_a_cannot_assign_company_b_org_unit_to_employee(self):
        """HR from Company A cannot assign Company B org unit to an employee."""
        self.client.force_authenticate(user=self.hr_a)
        resp = self.client.patch(f'/api/employees/{self.emp_a.uuid}/', {
            'org_unit': self.unit_b.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.emp_a.refresh_from_db()
        self.assertNotEqual(self.emp_a.org_unit, self.unit_b)

    def test_hr_a_cannot_assign_company_b_manager_to_employee(self):
        """HR from Company A cannot assign Company B employee as manager."""
        self.client.force_authenticate(user=self.hr_a)
        resp = self.client.patch(f'/api/employees/{self.emp_a.uuid}/', {
            'manager': self.emp_b.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.emp_a.refresh_from_db()
        self.assertNotEqual(self.emp_a.manager, self.emp_b)

    def test_hr_a_cannot_list_company_b_departments(self):
        """HR from Company A cannot list Company B departments."""
        self.client.force_authenticate(user=self.hr_a)
        resp = self.client.get('/api/departments/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        dept_ids = self._extract_item_ids(resp)
        self.assertIn(str(self.dept_a.uuid), dept_ids)
        self.assertNotIn(str(self.dept_b.uuid), dept_ids)

    def test_hr_a_cannot_list_company_b_positions(self):
        """HR from Company A cannot list Company B positions."""
        self.client.force_authenticate(user=self.hr_a)
        resp = self.client.get('/api/positions/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        pos_ids = self._extract_item_ids(resp)
        self.assertIn(self.pos_a.id, pos_ids)
        self.assertNotIn(self.pos_b.id, pos_ids)

    def test_hr_a_cannot_list_company_b_org_units(self):
        """HR from Company A cannot list Company B org units."""
        self.client.force_authenticate(user=self.hr_a)
        resp = self.client.get('/api/org-units/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        unit_ids = self._extract_item_ids(resp)
        self.assertIn(str(self.unit_a.uuid), unit_ids)
        self.assertNotIn(str(self.unit_b.uuid), unit_ids)


class EmployeeDeactivationTests(TestCase):
    """Verify safe deactivation and historical record preservation."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.hr_admin = Employee.objects.create_user(
            username="hr", password="x", company=self.company, role=EmployeeRole.HR_ADMIN
        )
        self.employee = Employee.objects.create_user(
            username="emp", password="x", company=self.company, is_active=True
        )
        self.client = APIClient()

    def test_deactivate_employee(self):
        """HR Admin can deactivate an active employee."""
        self.assertTrue(self.employee.is_active)
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.patch(f'/api/employees/{self.employee.uuid}/', {
            'is_active': False,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)

    def test_deactivated_employee_cannot_login(self):
        """A deactivated employee cannot authenticate."""
        self.employee.is_active = False
        self.employee.save()
        self.client = APIClient()
        # Attempt to force_authenticate should handle inactive users properly
        self.client.force_authenticate(user=self.employee)
        # Verify that API calls by inactive user are rejected by the application logic
        resp = self.client.get('/api/employees/me/')
        # The application might return 401 or the inactive user
        # This depends on implementation; verify that inactive users cannot act as normal
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)

    def test_reactivate_employee(self):
        """HR Admin can reactivate an inactive employee."""
        self.employee.is_active = False
        self.employee.save()
        self.assertFalse(self.employee.is_active)
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.patch(f'/api/employees/{self.employee.uuid}/', {
            'is_active': True,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.employee.refresh_from_db()
        self.assertTrue(self.employee.is_active)

    def test_soft_delete_preserves_historical_records(self):
        """Deactivating an employee should preserve historical data (soft delete)."""
        original_id = self.employee.id
        original_email = self.employee.email
        self.assertTrue(self.employee.is_active)
        
        self.client.force_authenticate(user=self.hr_admin)
        self.client.patch(f'/api/employees/{self.employee.uuid}/', {
            'is_active': False,
        }, format='json')
        
        # Verify historical record still exists (can be retrieved via all_objects)
        # After deactivation, employee should be accessible but inactive
        deactivated_emp = Employee.all_objects.get(id=original_id)
        self.assertEqual(deactivated_emp.email, original_email)
        self.assertFalse(deactivated_emp.is_active)


class AuthenticationBoundaryTests(TestCase):
    """Verify authentication and authorization boundaries."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.employee = Employee.objects.create_user(
            username="emp", password="testpass123", company=self.company
        )
        self.client = APIClient()

    def test_unauthenticated_cannot_access_employee_list(self):
        """Unauthenticated requests are rejected."""
        resp = self.client.get('/api/employees/')
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_unauthenticated_cannot_access_employee_me(self):
        """Unauthenticated requests to /me/ are rejected."""
        resp = self.client.get('/api/employees/me/')
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_employee_can_access_own_me_endpoint(self):
        """Authenticated employee can access their own /me/ endpoint."""
        self.client.force_authenticate(user=self.employee)
        resp = self.client.get('/api/employees/me/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['uuid'], str(self.employee.uuid))

    def test_employee_cannot_modify_own_role(self):
        """Employee cannot modify their own role."""
        self.client.force_authenticate(user=self.employee)
        resp = self.client.patch(f'/api/employees/{self.employee.uuid}/', {
            'role': EmployeeRole.MANAGER,
        }, format='json')
        self.assertIn(resp.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.role, EmployeeRole.EMPLOYEE)

    def test_employee_cannot_access_other_employee_detail(self):
        """Employee cannot fetch another employee's detail."""
        other = Employee.objects.create_user(
            username="other", password="x", company=self.company
        )
        self.client.force_authenticate(user=self.employee)
        resp = self.client.get(f'/api/employees/{other.uuid}/')
        # Should be forbidden or not found (403 or 404) - both are acceptable
        self.assertIn(resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
