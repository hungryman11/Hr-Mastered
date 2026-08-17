from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Company, Employee, EmployeeRole, OrgUnit, Position,
    KpiCategory, KpiTemplate, KpiFramework, KpiFrameworkItem,
    EmployeeKpiOverride, PerformanceCycle,
)
from core.kpi_service import KpiAssignmentService


@override_settings(ZOHO_USE_MOCK=True)
class KpiPreviewAndResolutionTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Acme Corp')
        self.other_company = Company.objects.create(name='Competitor Corp')

        # Company Employees
        self.hr = Employee.objects.create_user(
            username='hr_admin', email='hr@acme.com', password='password123',
            company=self.company, role=EmployeeRole.HR_ADMIN,
        )
        self.manager = Employee.objects.create_user(
            username='tech_lead', email='lead@acme.com', password='password123',
            company=self.company, role=EmployeeRole.MANAGER,
        )
        self.dept_unit = OrgUnit.objects.create(
            company=self.company, name='Engineering',
            unit_type=OrgUnit.UnitType.DEPARTMENT, head=self.manager,
        )
        self.position = Position.objects.create(
            company=self.company, org_unit=self.dept_unit,
            title='Backend Developer', code='DEV-BE',
        )
        self.employee1 = Employee.objects.create_user(
            username='dev_alice', email='alice@acme.com', password='password123',
            company=self.company, role=EmployeeRole.EMPLOYEE,
            org_unit=self.dept_unit, position=self.position, manager=self.manager,
        )
        self.employee2 = Employee.objects.create_user(
            username='dev_bob', email='bob@acme.com', password='password123',
            company=self.company, role=EmployeeRole.EMPLOYEE,
            org_unit=self.dept_unit, position=self.position, manager=None,
        )

        # Other Company Employee
        self.other_emp = Employee.objects.create_user(
            username='other_emp', email='other@comp.com', password='password123',
            company=self.other_company, role=EmployeeRole.EMPLOYEE,
        )

        # KPI Category & Templates
        self.category = KpiCategory.objects.create(company=self.company, name='Engineering Core')
        self.tmpl_global = KpiTemplate.objects.create(
            company=self.company, name='Company Values Alignment',
            category=self.category, measurement_type=KpiTemplate.MeasurementType.RATING,
            default_target='4.0', default_weight=20, min_score=0, max_score=100,
        )
        self.tmpl_dept = KpiTemplate.objects.create(
            company=self.company, name='Code Quality & Test Coverage',
            category=self.category, measurement_type=KpiTemplate.MeasurementType.PERCENT,
            default_target='85', default_weight=30, min_score=0, max_score=100,
        )
        self.tmpl_pos = KpiTemplate.objects.create(
            company=self.company, name='API Latency SLA',
            category=self.category, measurement_type=KpiTemplate.MeasurementType.NUMERIC,
            default_target='200', default_weight=30, min_score=0, max_score=120,
        )
        self.tmpl_extra = KpiTemplate.objects.create(
            company=self.company, name='Mentorship & Hiring',
            category=self.category, measurement_type=KpiTemplate.MeasurementType.NUMERIC,
            default_target='5', default_weight=20, min_score=0, max_score=100,
        )

        # Global Framework (Weight 20)
        self.global_fw = KpiFramework.objects.create(
            company=self.company, name='Global Standards',
            scope_type=KpiFramework.ScopeType.GLOBAL, status=KpiFramework.Status.PUBLISHED,
        )
        KpiFrameworkItem.objects.create(framework=self.global_fw, template=self.tmpl_global, weight=20, target='4.0')

        # Department Framework (Weight 30)
        self.dept_fw = KpiFramework.objects.create(
            company=self.company, name='Engineering Framework',
            scope_type=KpiFramework.ScopeType.DEPARTMENT, org_unit=self.dept_unit,
            status=KpiFramework.Status.PUBLISHED,
        )
        KpiFrameworkItem.objects.create(framework=self.dept_fw, template=self.tmpl_dept, weight=30, target='85')

        # Position Framework (Weight 50)
        self.pos_fw = KpiFramework.objects.create(
            company=self.company, name='Backend Dev Framework',
            scope_type=KpiFramework.ScopeType.POSITION, position=self.position,
            status=KpiFramework.Status.PUBLISHED,
        )
        KpiFrameworkItem.objects.create(framework=self.pos_fw, template=self.tmpl_pos, weight=50, target='200')

        self.cycle = PerformanceCycle.objects.create(
            company=self.company, name='2026 Annual Cycle',
            start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        )

        self.client = APIClient()

    def test_four_level_inheritance_and_provenance(self):
        """
        Verify Global -> Department -> Position -> Employee Overrides (ADD, MODIFY, REMOVE).
        """
        # Add an override modifying Position KPI (weight 30), adding Extra KPI (weight 20)
        EmployeeKpiOverride.objects.create(
            company=self.company, employee=self.employee1, template=self.tmpl_pos,
            action_type=EmployeeKpiOverride.ActionType.MODIFY, weight=30, target='150',
        )
        EmployeeKpiOverride.objects.create(
            company=self.company, employee=self.employee1, template=self.tmpl_extra,
            action_type=EmployeeKpiOverride.ActionType.ADD, weight=20, target='10',
        )

        preview = KpiAssignmentService.get_effective_kpis_preview(self.employee1)

        # Expected weights: Global (20) + Dept (30) + Pos Override (30) + Extra Override (20) = 100
        self.assertEqual(preview['total_weight'], 100.0)
        self.assertTrue(preview['is_valid_total_weight'])
        self.assertEqual(len(preview['items']), 4)
        self.assertEqual(len(preview['issues']), 0)

        # Verify provenance tags
        sources = {item['template_name']: item['source']['scope'] for item in preview['items']}
        self.assertEqual(sources['Company Values Alignment'], 'GLOBAL')
        self.assertEqual(sources['Code Quality & Test Coverage'], 'DEPARTMENT')
        self.assertEqual(sources['API Latency SLA'], 'EMPLOYEE_OVERRIDE')
        self.assertEqual(sources['Mentorship & Hiring'], 'EMPLOYEE_OVERRIDE')

    def test_override_remove_action(self):
        """
        Verify that REMOVE action type cleanly eliminates an inherited KPI.
        """
        EmployeeKpiOverride.objects.create(
            company=self.company, employee=self.employee1, template=self.tmpl_global,
            action_type=EmployeeKpiOverride.ActionType.REMOVE,
        )

        preview = KpiAssignmentService.get_effective_kpis_preview(self.employee1)
        item_names = [i['template_name'] for i in preview['items']]
        self.assertNotIn('Company Values Alignment', item_names)
        # Total weight is now 30 + 50 = 80, which is invalid (< 100)
        self.assertEqual(preview['total_weight'], 80.0)
        self.assertFalse(preview['is_valid_total_weight'])
        self.assertTrue(any('must equal 100%' in issue for issue in preview['issues']))

    def test_employee_effective_kpis_endpoint_permissions(self):
        """
        HR Admin can view any employee.
        Manager can view their direct reports.
        Employee can view self.
        Employee cannot view other employees (403).
        Cross-company access returns 404.
        """
        url_alice = f'/api/employees/{self.employee1.uuid}/effective_kpis/'
        url_bob = f'/api/employees/{self.employee2.uuid}/effective_kpis/'
        url_other = f'/api/employees/{self.other_emp.uuid}/effective_kpis/'

        # 1. HR Admin access -> 200 OK
        self.client.force_authenticate(user=self.hr)
        resp = self.client.get(url_alice)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['employee_uuid'], str(self.employee1.uuid))
        self.assertEqual(resp.data['total_weight'], 100.0)
        self.assertTrue(resp.data['is_valid_total_weight'])

        # 2. Manager access to report (Alice) -> 200 OK
        self.client.force_authenticate(user=self.manager)
        resp = self.client.get(url_alice)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # 3. Manager access to non-report (Bob) -> 403 Forbidden (or 404 if filtered out of queryset)
        resp = self.client.get(url_bob)
        self.assertIn(resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

        # 4. Employee access to self -> 200 OK
        self.client.force_authenticate(user=self.employee1)
        resp = self.client.get(url_alice)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # 5. Employee access to peer (Bob) -> 403 / 404
        resp = self.client.get(url_bob)
        self.assertIn(resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

        # 6. Cross-company access -> 404
        self.client.force_authenticate(user=self.hr)
        resp = self.client.get(url_other)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cycle_preview_assignments_endpoint(self):
        """
        HR Admin can preview company-wide assignment generation with valid/invalid metrics.
        """
        url = f'/api/performance-cycles/{self.cycle.uuid}/preview_assignments/'

        # 1. Non-HR user gets 403
        self.client.force_authenticate(user=self.employee1)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # 2. HR Admin gets 200 OK
        self.client.force_authenticate(user=self.hr)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['cycle_uuid'], str(self.cycle.uuid))
        self.assertIn('previews', resp.data)
        self.assertIn('valid_employees', resp.data)
        self.assertIn('can_generate_assignments', resp.data)

    def test_effective_date_query_param(self):
        """
        as_of_date query parameter properly filters time-bound overrides.
        """
        # Create an override effective in 2027 only
        EmployeeKpiOverride.objects.create(
            company=self.company, employee=self.employee1, template=self.tmpl_pos,
            action_type=EmployeeKpiOverride.ActionType.MODIFY, weight=40, target='100',
            effective_from=date(2027, 1, 1), effective_to=date(2027, 12, 31),
        )

        self.client.force_authenticate(user=self.hr)
        url_2026 = f'/api/employees/{self.employee1.uuid}/effective_kpis/?as_of_date=2026-06-01'
        url_2027 = f'/api/employees/{self.employee1.uuid}/effective_kpis/?as_of_date=2027-06-01'

        resp_2026 = self.client.get(url_2026)
        self.assertEqual(resp_2026.status_code, status.HTTP_200_OK)
        # In 2026, position weight is still 50
        pos_item_2026 = next(i for i in resp_2026.data['items'] if i['template_name'] == 'API Latency SLA')
        self.assertEqual(pos_item_2026['weight'], 50.0)

        resp_2027 = self.client.get(url_2027)
        self.assertEqual(resp_2027.status_code, status.HTTP_200_OK)
        # In 2027, position weight is modified to 40
        pos_item_2027 = next(i for i in resp_2027.data['items'] if i['template_name'] == 'API Latency SLA')
        self.assertEqual(pos_item_2027['weight'], 40.0)
