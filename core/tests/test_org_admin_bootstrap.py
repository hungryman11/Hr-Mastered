from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from core.models import Company, Employee, EmployeeRole


class CreateOrgAdminCommandTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Infinity Microfinance Bank')

    def test_create_org_admin_creates_account(self):
        call_command(
            'create_org_admin',
            '--company', self.company.name,
            '--first-name', 'Jane',
            '--last-name', 'Doe',
            '--username', 'jane.doe',
            '--email', 'jane.doe@infinity.local',
            '--password', 'StrongPassword123!'
        )

        employee = Employee.objects.get(username='jane.doe')
        self.assertEqual(employee.company, self.company)
        self.assertTrue(employee.is_active)
        self.assertTrue(employee.is_org_admin)
        self.assertEqual(employee.role, EmployeeRole.HR_ADMIN)

    def test_create_org_admin_rejects_unknown_company(self):
        with self.assertRaises(CommandError):
            call_command(
                'create_org_admin',
                '--company', 'Missing Company',
                '--first-name', 'Jane',
                '--last-name', 'Doe',
                '--username', 'jane.doe',
                '--email', 'jane.doe@infinity.local',
                '--password', 'StrongPassword123!'
            )

    def test_create_org_admin_rejects_weak_password(self):
        with self.assertRaises(CommandError):
            call_command(
                'create_org_admin',
                '--company', self.company.name,
                '--first-name', 'Jane',
                '--last-name', 'Doe',
                '--username', 'jane.doe',
                '--email', 'jane.doe@infinity.local',
                '--password', 'short'
            )
