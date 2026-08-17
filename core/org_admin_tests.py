"""
Tests for the ORG_ADMIN permission tier.

Context: OrgUnit writes and reassigning an existing employee's role/manager/
org_unit used to require only IsHRAdmin. That's now split: those specific
actions require IsOrgAdmin (an independent `is_org_admin` flag), which is
narrower than IsHRAdmin and only grantable by a superuser via
EmployeeViewSet.set_org_admin. Ordinary HR administration (leave types,
leave balances, holidays, etc.) is deliberately untouched by this change.

Test taxonomy
─────────────
happy_path:  request succeeds and response shape matches the API contract
boundary:    request at the edge of a valid / invalid boundary
error:       request that should be rejected with an appropriate status code
"""
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Company, Employee, EmployeeRole, OrgUnit


class OrgAdminPermissionTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Org Admin Co")
        self.hr_admin = Employee.objects.create_user(
            username="plain_hr", password="x", company=self.company, role=EmployeeRole.HR_ADMIN
        )
        self.org_admin = Employee.objects.create_user(
            username="org_admin_hr", password="x", company=self.company,
            role=EmployeeRole.HR_ADMIN, is_org_admin=True,
        )
        self.superuser = Employee.objects.create_superuser(
            username="root", password="x", email="root@example.com", company=self.company,
        )
        self.unit = OrgUnit.objects.create(company=self.company, name="Engineering", unit_type=OrgUnit.UnitType.DEPARTMENT)
        self.client = APIClient()

    # ── OrgUnit writes ───────────────────────────────────────────────────────

    def test_plain_hr_admin_cannot_create_org_unit_error(self):
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.post('/api/org-units/', data={'name': 'New Unit', 'unit_type': OrgUnit.UnitType.TEAM})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_org_admin_can_create_org_unit_happy_path(self):
        self.client.force_authenticate(user=self.org_admin)
        resp = self.client.post('/api/org-units/', data={'name': 'New Unit', 'unit_type': OrgUnit.UnitType.TEAM})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_plain_hr_admin_cannot_delete_org_unit_error(self):
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.delete(f'/api/org-units/{self.unit.uuid}/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_plain_hr_admin_can_still_read_org_units_happy_path(self):
        """Narrowing writes must not remove ordinary read access for HR Admins."""
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.get('/api/org-units/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_superuser_can_create_org_unit_happy_path(self):
        self.client.force_authenticate(user=self.superuser)
        resp = self.client.post('/api/org-units/', data={'name': 'Root Unit', 'unit_type': OrgUnit.UnitType.TEAM})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    # ── Employee role/manager/org_unit reassignment ─────────────────────────

    def test_plain_hr_admin_cannot_change_existing_employee_role_error(self):
        target = Employee.objects.create_user(username="target1", password="x", company=self.company, role=EmployeeRole.EMPLOYEE)
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.patch(f'/api/employees/{target.uuid}/', data={'role': EmployeeRole.MANAGER}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        target.refresh_from_db()
        self.assertEqual(target.role, EmployeeRole.EMPLOYEE)

    def test_plain_hr_admin_cannot_change_existing_employee_manager_error(self):
        target = Employee.objects.create_user(username="target2", password="x", company=self.company)
        new_manager = Employee.objects.create_user(username="mgr1", password="x", company=self.company, role=EmployeeRole.MANAGER)
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.patch(f'/api/employees/{target.uuid}/', data={'manager': new_manager.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_org_admin_can_change_existing_employee_role_happy_path(self):
        target = Employee.objects.create_user(username="target3", password="x", company=self.company, role=EmployeeRole.EMPLOYEE)
        self.client.force_authenticate(user=self.org_admin)
        resp = self.client.patch(f'/api/employees/{target.uuid}/', data={'role': EmployeeRole.MANAGER}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        target.refresh_from_db()
        self.assertEqual(target.role, EmployeeRole.MANAGER)

    def test_plain_hr_admin_can_still_change_other_fields_happy_path(self):
        """Only role/manager/org_unit are gated - ordinary HR edits (e.g. first_name)
        must keep working for a plain HR Admin."""
        target = Employee.objects.create_user(username="target4", password="x", company=self.company)
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.patch(f'/api/employees/{target.uuid}/', data={'first_name': 'Updated'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        target.refresh_from_db()
        self.assertEqual(target.first_name, 'Updated')

    def test_plain_hr_admin_can_still_set_role_at_creation_happy_path(self):
        """The gate only applies to *changing* an already-persisted employee, not to
        initial values set during normal HR onboarding (create)."""
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.post('/api/employees/', data={
            'username': 'newhire1', 'first_name': 'New', 'last_name': 'Hire',
            'email': 'newhire1@orgadminco.com', 'role': EmployeeRole.MANAGER,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['role'], EmployeeRole.MANAGER)

    def test_patch_with_unchanged_role_value_not_blocked_boundary(self):
        """Resubmitting the same role/manager/org_unit value (a no-op) must not be
        treated as a change requiring org-admin."""
        target = Employee.objects.create_user(username="target5", password="x", company=self.company, role=EmployeeRole.EMPLOYEE)
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.patch(f'/api/employees/{target.uuid}/', data={'role': EmployeeRole.EMPLOYEE}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # ── Granting/revoking is_org_admin itself ───────────────────────────────

    def test_is_org_admin_is_read_only_on_general_patch_error(self):
        """is_org_admin must never be settable through the general employee PATCH,
        even by an org admin - only through the dedicated superuser-only action."""
        target = Employee.objects.create_user(username="target6", password="x", company=self.company)
        self.client.force_authenticate(user=self.org_admin)
        resp = self.client.patch(f'/api/employees/{target.uuid}/', data={'is_org_admin': True}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        target.refresh_from_db()
        self.assertFalse(target.is_org_admin)

    def test_org_admin_cannot_grant_org_admin_to_others_error(self):
        """Deliberately superuser-only: an existing org admin cannot mint more."""
        target = Employee.objects.create_user(username="target7", password="x", company=self.company)
        self.client.force_authenticate(user=self.org_admin)
        resp = self.client.post(f'/api/employees/{target.uuid}/set_org_admin/', data={'is_org_admin': True}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_hr_admin_cannot_grant_org_admin_error(self):
        target = Employee.objects.create_user(username="target8", password="x", company=self.company)
        self.client.force_authenticate(user=self.hr_admin)
        resp = self.client.post(f'/api/employees/{target.uuid}/set_org_admin/', data={'is_org_admin': True}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_grant_org_admin_happy_path(self):
        target = Employee.objects.create_user(username="target9", password="x", company=self.company)
        self.client.force_authenticate(user=self.superuser)
        resp = self.client.post(f'/api/employees/{target.uuid}/set_org_admin/', data={'is_org_admin': True}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        target.refresh_from_db()
        self.assertTrue(target.is_org_admin)

    def test_superuser_can_revoke_org_admin_happy_path(self):
        self.client.force_authenticate(user=self.superuser)
        resp = self.client.post(f'/api/employees/{self.org_admin.uuid}/set_org_admin/', data={'is_org_admin': False}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.org_admin.refresh_from_db()
        self.assertFalse(self.org_admin.is_org_admin)

    def test_set_org_admin_requires_boolean_error(self):
        target = Employee.objects.create_user(username="target10", password="x", company=self.company)
        self.client.force_authenticate(user=self.superuser)
        resp = self.client.post(f'/api/employees/{target.uuid}/set_org_admin/', data={'is_org_admin': 'yes'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_set_org_admin_requires_field_error(self):
        target = Employee.objects.create_user(username="target11", password="x", company=self.company)
        self.client.force_authenticate(user=self.superuser)
        resp = self.client.post(f'/api/employees/{target.uuid}/set_org_admin/', data={}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_cannot_hit_org_units_error(self):
        resp = self.client.post('/api/org-units/', data={'name': 'X', 'unit_type': OrgUnit.UnitType.TEAM})
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
