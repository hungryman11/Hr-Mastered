from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from core.models import Company, Employee, EmployeeRole, KpiTemplate, KpiFramework, KpiFrameworkItem, OrgUnit, Position, EmployeeKpiOverride

class KpiPermissionsPrecedenceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='PermCo')
        self.hr = Employee.objects.create_user(username='hr', email='hr@perm.co', password='x', company=self.company, role=EmployeeRole.HR_ADMIN)
        self.emp = Employee.objects.create_user(username='emp', email='emp@perm.co', password='x', company=self.company, role=EmployeeRole.EMPLOYEE)
        self.client = APIClient()

    def test_non_hr_cannot_create_framework(self):
        self.client.force_authenticate(user=self.emp)
        resp = self.client.post('/api/kpi-frameworks/', {'name': 'X', 'scope_type': 'GLOBAL'})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        # HR can create
        self.client.force_authenticate(user=self.hr)
        resp2 = self.client.post('/api/kpi-frameworks/', {'name': 'X', 'scope_type': 'GLOBAL'})
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)

    def test_precedence_rules_global_ancestor_position_employee(self):
        # hierarchy: parent -> child
        parent = OrgUnit.objects.create(company=self.company, name='Parent', unit_type=OrgUnit.UnitType.DEPARTMENT)
        child = OrgUnit.objects.create(company=self.company, name='Child', unit_type=OrgUnit.UnitType.DEPARTMENT, parent=parent)
        # position
        pos = Position.objects.create(company=self.company, title='Engineer')
        # assign employee to child unit and position
        self.emp.org_unit = child
        self.emp.position = pos
        self.emp.save()

        cat_template = KpiTemplate.objects.create(company=self.company, name='Prec', default_weight=100)
        # global framework
        gw = KpiFramework.objects.create(company=self.company, name='GlobalFW', scope_type=KpiFramework.ScopeType.GLOBAL, status=KpiFramework.Status.PUBLISHED)
        KpiFrameworkItem.objects.create(framework=gw, template=cat_template, weight=100, target='g')
        # ancestor framework on parent
        aw = KpiFramework.objects.create(company=self.company, name='AncestorFW', scope_type=KpiFramework.ScopeType.DEPARTMENT, org_unit=parent, status=KpiFramework.Status.PUBLISHED)
        KpiFrameworkItem.objects.create(framework=aw, template=cat_template, weight=100, target='a')
        # position framework
        pw = KpiFramework.objects.create(company=self.company, name='PosFW', scope_type=KpiFramework.ScopeType.POSITION, position=pos, status=KpiFramework.Status.PUBLISHED)
        KpiFrameworkItem.objects.create(framework=pw, template=cat_template, weight=100, target='p')
        # employee override
        EmployeeKpiOverride.objects.create(company=self.company, employee=self.emp, template=cat_template, weight=100, target='e')

        cycle = KpiFramework.objects.model._meta.apps.get_model('core', 'PerformanceCycle').objects.create(company=self.company, name='C', start_date='2026-01-01', end_date='2026-12-31')
        self.client.force_authenticate(user=self.hr)
        resp = self.client.post(f'/api/performance-cycles/{cycle.uuid}/generate_assignments/')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data
        self.assertTrue(any((a.get('template') == cat_template.id or a.get('template') == str(cat_template.uuid)) and (a.get('weight') == 100 or float(a.get('weight')) == 100.0) and a.get('target') == 'e' for a in data))
