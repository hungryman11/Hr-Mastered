from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status

from core.models import Company, Employee, EmployeeRole, KpiCategory, KpiTemplate, KpiFramework, PerformanceCycle, OrgUnit, Position, KpiFrameworkItem


@override_settings(ZOHO_USE_MOCK=True)
class KpiInheritanceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='KPI Inherit Co')
        self.hr = Employee.objects.create_user(username='hr', email='hr@example.com', password='x', company=self.company, role=EmployeeRole.HR_ADMIN)
        self.manager = Employee.objects.create_user(username='mgr', email='mgr@example.com', password='x', company=self.company, role=EmployeeRole.MANAGER)
        self.unit = OrgUnit.objects.create(company=self.company, name='Engineering', unit_type=OrgUnit.UnitType.DEPARTMENT, head=self.manager)
        self.position = Position.objects.create(company=self.company, title='Senior Developer', org_unit=self.unit)
        self.employee = Employee.objects.create_user(username='emp', email='emp@example.com', password='x', company=self.company, role=EmployeeRole.EMPLOYEE, org_unit=self.unit, position=self.position, manager=self.manager)
        self.client = APIClient()

    def test_position_framework_overrides_department(self):
        """
        When both a DEPARTMENT and a POSITION framework define the same
        KPI template, the POSITION framework value must win (the template_id
        key is overwritten in the merge dict).  Total weight must still equal
        100 % so that assignment generation succeeds.
        """
        # Single shared template
        tmpl = KpiTemplate.objects.create(
            company=self.company,
            name='Shared Metric',
            measurement_type=KpiTemplate.MeasurementType.NUMERIC,
            default_weight=100,
        )

        # Department framework — target '50', weight 100
        dept_fw = KpiFramework.objects.create(
            company=self.company,
            name='Dept FW',
            scope_type='DEPARTMENT',
            org_unit=self.unit,
            status='PUBLISHED',
        )
        KpiFrameworkItem.objects.create(framework=dept_fw, template=tmpl, weight=100, target='50')

        # Position framework — same template, target '80', weight 100 (should win)
        pos_fw = KpiFramework.objects.create(
            company=self.company,
            name='Pos FW',
            scope_type='POSITION',
            position=self.position,
            status='PUBLISHED',
        )
        KpiFrameworkItem.objects.create(framework=pos_fw, template=tmpl, weight=100, target='80')

        cycle = PerformanceCycle.objects.create(
            company=self.company,
            name='Cycle',
            start_date='2026-01-01',
            end_date='2026-06-30',
        )

        self.client.force_authenticate(user=self.hr)
        resp = self.client.post(f'/api/performance-cycles/{cycle.uuid}/generate_assignments/')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data

        # One assignment for our employee
        emp_assignments = [a for a in data if a['employee'] == self.employee.id or a.get('employee') == str(getattr(self.employee, 'uuid', None))]
        self.assertEqual(len(emp_assignments), 1, "Expected exactly one assignment (POSITION supersedes DEPT for same template)")
        assignment = emp_assignments[0]
        # The position framework's target ('80') must have overridden the dept's ('50')
        self.assertEqual(str(assignment['target']), '80', "Position framework target must override department framework target")