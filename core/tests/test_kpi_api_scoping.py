from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from core.models import Company, Employee, EmployeeRole, KpiFramework

class KpiApiScopingTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='ScopeCo')
        self.other = Company.objects.create(name='OtherCo')
        self.hr = Employee.objects.create_user(username='hr', email='hr@scope.co', password='x', company=self.company, role=EmployeeRole.HR_ADMIN)
        self.other_hr = Employee.objects.create_user(username='oh', email='oh@other.co', password='x', company=self.other, role=EmployeeRole.HR_ADMIN)
        # frameworks
        self.fw_ours = KpiFramework.objects.create(company=self.company, name='Our FW', scope_type='DEPARTMENT')
        self.fw_other = KpiFramework.objects.create(company=self.other, name='Other FW', scope_type='DEPARTMENT')
        self.client = APIClient()

    def test_framework_list_scoped_to_user_company(self):
        self.client.force_authenticate(user=self.hr)
        resp = self.client.get('/api/kpi-frameworks/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        names = [r.get('name') for r in resp.data]
        self.assertIn('Our FW', names)
        self.assertNotIn('Other FW', names)

    def test_override_list_scoped(self):
        # create an override in other company and ensure our user doesn't see it
        from core.models import EmployeeKpiOverride, KpiTemplate, Employee
        tmpl = KpiTemplate.objects.create(company=self.other, name='T1')
        other_emp = Employee.objects.create_user(username='oemp', email='oemp@other.co', password='x', company=self.other)
        EmployeeKpiOverride.objects.create(company=self.other, employee=other_emp, template=tmpl, weight=10)
        self.client.force_authenticate(user=self.hr)
        resp = self.client.get('/api/kpi-employee-overrides/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)
