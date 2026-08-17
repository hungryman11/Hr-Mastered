from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status

from core.models import Company, Employee, EmployeeRole, KpiCategory, KpiTemplate, KpiFramework, PerformanceCycle, OrgUnit, KpiFrameworkItem, EmployeeKpiOverride
from core.models import EmployeeKpiAssignment


@override_settings(ZOHO_USE_MOCK=True)
class KpiOverrideTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='KPI Override Co')
        self.hr = Employee.objects.create_user(username='hr', email='hr@example.com', password='x', company=self.company, role=EmployeeRole.HR_ADMIN)
        self.manager = Employee.objects.create_user(username='mgr', email='mgr@example.com', password='x', company=self.company, role=EmployeeRole.MANAGER)
        self.unit = OrgUnit.objects.create(company=self.company, name='Engineering', unit_type=OrgUnit.UnitType.DEPARTMENT, head=self.manager)
        # regular employee to receive assignments
        self.employee = Employee.objects.create_user(username='emp', email='emp@example.com', password='x', company=self.company, role=EmployeeRole.EMPLOYEE, org_unit=self.unit, manager=self.manager)
        self.client = APIClient()

    def test_employee_override_applies(self):
        cat = KpiCategory.objects.create(company=self.company, name='Quality')
        tmpl = KpiTemplate.objects.create(company=self.company, name='Accuracy', measurement_type=KpiTemplate.MeasurementType.NUMERIC, default_weight=10, category=cat)

        # department framework with template weight 100
        fw = KpiFramework.objects.create(company=self.company, name='Dept FW', scope_type='DEPARTMENT', org_unit=self.unit, status='PUBLISHED')
        KpiFrameworkItem.objects.create(framework=fw, template=tmpl, weight=100, target='95')

        # employee override changes the target but keeps weight=100 so total stays 100%
        EmployeeKpiOverride.objects.create(
            company=self.company,
            employee=self.employee,
            template=tmpl,
            weight=100,
            target='50',
            action_type=EmployeeKpiOverride.ActionType.MODIFY,
        )

        cycle = PerformanceCycle.objects.create(company=self.company, name='2026 H1', start_date='2026-01-01', end_date='2026-06-30')

        self.client.force_authenticate(user=self.hr)
        resp = self.client.post(f'/api/performance-cycles/{cycle.uuid}/generate_assignments/')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data
        # The override target ('50') should appear on the assignment
        self.assertTrue(any(
            (a.get('template') == tmpl.id or a.get('template') == str(tmpl.uuid))
            and str(a.get('target')) == '50'
            for a in data
        ))

        # verify snapshot fields on created assignment
        assignment = EmployeeKpiAssignment.objects.filter(cycle=cycle, employee=self.employee, template=tmpl).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.template_name, tmpl.name)
        self.assertEqual(assignment.measurement_type, tmpl.measurement_type)
        self.assertEqual(assignment.direction, tmpl.direction)
        self.assertEqual(assignment.scoring_method, tmpl.scoring_method)
        self.assertEqual(assignment.template_description, tmpl.description)
        self.assertEqual(assignment.template_default_target, tmpl.default_target)
        self.assertEqual(float(assignment.template_default_weight), float(tmpl.default_weight))
        self.assertEqual(assignment.template_frequency, tmpl.frequency)
        self.assertEqual(assignment.template_data_source, tmpl.data_source)

    def test_override_effective_dates_and_inactive(self):
        cat = KpiCategory.objects.create(company=self.company, name='Delivery')
        tmpl = KpiTemplate.objects.create(company=self.company, name='Speed', measurement_type=KpiTemplate.MeasurementType.NUMERIC, default_weight=20, category=cat)
        fw = KpiFramework.objects.create(company=self.company, name='Dept FW', scope_type='DEPARTMENT', org_unit=self.unit, status='PUBLISHED')
        KpiFrameworkItem.objects.create(framework=fw, template=tmpl, weight=100, target='5')

        # future-dated override should NOT apply
        from datetime import date, timedelta
        future = date.today() + timedelta(days=30)
        EmployeeKpiOverride.objects.create(
            company=self.company,
            employee=self.employee,
            template=tmpl,
            weight=10,
            target='3',
            effective_from=future,
            action_type=EmployeeKpiOverride.ActionType.MODIFY,
        )

        cycle = PerformanceCycle.objects.create(company=self.company, name='2026 H2', start_date='2026-07-01', end_date='2026-12-31')
        self.client.force_authenticate(user=self.hr)
        resp = self.client.post(f'/api/performance-cycles/{cycle.uuid}/generate_assignments/')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data
        # assignment weight should remain 100 from framework (future override not applied)
        self.assertTrue(any((a.get('template') == tmpl.id or a.get('template') == str(tmpl.uuid)) and (a.get('weight') == 100 or float(a.get('weight')) == 100.0) for a in data))

        # inactive override should NOT apply
        EmployeeKpiOverride.objects.all().hard_delete()
        EmployeeKpiOverride.objects.create(
            company=self.company,
            employee=self.employee,
            template=tmpl,
            weight=10,
            target='3',
            active=False,
            action_type=EmployeeKpiOverride.ActionType.MODIFY,
        )
        cycle2 = PerformanceCycle.objects.create(company=self.company, name='2027 H1', start_date='2027-01-01', end_date='2027-06-30')
        resp2 = self.client.post(f'/api/performance-cycles/{cycle2.uuid}/generate_assignments/')
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        data2 = resp2.data
        self.assertTrue(any((a.get('template') == tmpl.id or a.get('template') == str(tmpl.uuid)) and (a.get('weight') == 100 or float(a.get('weight')) == 100.0) for a in data2))

    def test_assignment_snapshot_immutable(self):
        cat = KpiCategory.objects.create(company=self.company, name='Eng')
        tmpl = KpiTemplate.objects.create(company=self.company, name='Quality2', measurement_type=KpiTemplate.MeasurementType.NUMERIC, default_weight=40, category=cat, default_target='70', description='orig')
        fw = KpiFramework.objects.create(company=self.company, name='Dept FW2', scope_type='DEPARTMENT', org_unit=self.unit, status='PUBLISHED')
        KpiFrameworkItem.objects.create(framework=fw, template=tmpl, weight=100, target='70')
        cycle = PerformanceCycle.objects.create(company=self.company, name='2026 H3', start_date='2026-07-01', end_date='2026-09-30')
        self.client.force_authenticate(user=self.hr)
        resp = self.client.post(f'/api/performance-cycles/{cycle.uuid}/generate_assignments/')
        self.assertEqual(resp.status_code, 201)
        assignment = EmployeeKpiAssignment.objects.get(cycle=cycle, employee=self.employee, template=tmpl)
        # change the template after snapshot
        tmpl.name = 'Changed Name'
        tmpl.description = 'changed'
        tmpl.default_target = '999'
        tmpl.default_weight = 1
        tmpl.save()
        # regenerate assignments
        resp2 = self.client.post(f'/api/performance-cycles/{cycle.uuid}/generate_assignments/')
        self.assertEqual(resp2.status_code, 201)
        assignment.refresh_from_db()
        # snapshot fields should remain the original values
        self.assertEqual(assignment.template_name, 'Quality2')
        self.assertEqual(assignment.template_description, 'orig')
        self.assertEqual(assignment.template_default_target, '70')
