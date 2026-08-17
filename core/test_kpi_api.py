from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status

from core.models import Company, Employee, EmployeeRole, KpiCategory, KpiTemplate, KpiFramework, PerformanceCycle, OrgUnit, KpiFrameworkItem


@override_settings(ZOHO_USE_MOCK=True)
class KpiApiTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='KPI Co')
        self.hr = Employee.objects.create_user(username='hr', email='hr@example.com', password='x', company=self.company, role=EmployeeRole.HR_ADMIN)
        self.manager = Employee.objects.create_user(username='mgr', email='mgr@example.com', password='x', company=self.company, role=EmployeeRole.MANAGER)
        self.unit = OrgUnit.objects.create(company=self.company, name='Engineering', unit_type=OrgUnit.UnitType.DEPARTMENT, head=self.manager)
        # regular employee to receive assignments
        self.employee = Employee.objects.create_user(username='emp', email='emp@example.com', password='x', company=self.company, role=EmployeeRole.EMPLOYEE, org_unit=self.unit, manager=self.manager)
        self.client = APIClient()

    def test_hr_can_create_and_update_framework(self):
        self.client.force_authenticate(user=self.hr)
        payload = {'name': 'Eng Framework', 'scope_type': 'DEPARTMENT', 'org_unit': self.unit.id}
        resp = self.client.post('/api/kpi-frameworks/', data=payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        fid = resp.data['uuid']

        # update
        resp2 = self.client.patch(f'/api/kpi-frameworks/{fid}/', data={'name': 'Updated Framework'}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.data['name'], 'Updated Framework')

    def test_generate_assignments_creates_snapshots(self):
        self.client.force_authenticate(user=self.hr)
        cat = KpiCategory.objects.create(company=self.company, name='Quality')
        tmpl = KpiTemplate.objects.create(company=self.company, name='Accuracy', measurement_type=KpiTemplate.MeasurementType.NUMERIC, default_weight=10, category=cat)

        # framework configuration references template uuid in expected structure
        config = [{'template': str(tmpl.uuid), 'weight': 50, 'target': '95'}]
        fw = KpiFramework.objects.create(company=self.company, name='Eng FW', scope_type='DEPARTMENT', org_unit=self.unit, status='PUBLISHED')
        # create structured item for the framework
        KpiFrameworkItem.objects.create(framework=fw, template=tmpl, weight=100, target='95')

        cycle = PerformanceCycle.objects.create(company=self.company, name='2026 H1', start_date='2026-01-01', end_date='2026-06-30')

        resp = self.client.post(f'/api/performance-cycles/{cycle.uuid}/generate_assignments/')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data
        # Should create at least one assignment for our employee (employee may be returned as PK or UUID)
        self.assertTrue(any(a['employee'] == self.employee.id or a.get('employee') == str(self.employee.uuid) for a in data))
