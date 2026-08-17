from decimal import Decimal
from datetime import date
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Company, Employee, EmployeeRole, OrgUnit, Position,
    KpiCategory, KpiTemplate, KpiFramework, KpiFrameworkItem,
    PerformanceCycle, EmployeeKpiAssignment, KpiMeasurement,
)
from core.kpi_scoring_service import KpiScoringService
from core.kpi_service import KpiAssignmentService


@override_settings(ZOHO_USE_MOCK=True)
class KpiScoringEngineTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Scoring Co')
        self.other_company = Company.objects.create(name='Other Co')

        self.hr = Employee.objects.create_user(
            username='hr_scoring', email='hr@scoring.com', password='password123',
            company=self.company, role=EmployeeRole.HR_ADMIN,
        )
        self.manager = Employee.objects.create_user(
            username='mgr_scoring', email='mgr@scoring.com', password='password123',
            company=self.company, role=EmployeeRole.MANAGER,
        )
        self.dept_unit = OrgUnit.objects.create(
            company=self.company, name='Operations',
            unit_type=OrgUnit.UnitType.DEPARTMENT, head=self.manager,
        )
        self.position = Position.objects.create(
            company=self.company, org_unit=self.dept_unit,
            title='Ops Lead', code='OPS-01',
        )
        self.employee1 = Employee.objects.create_user(
            username='emp_alice', email='alice@scoring.com', password='password123',
            company=self.company, role=EmployeeRole.EMPLOYEE,
            org_unit=self.dept_unit, position=self.position, manager=self.manager,
        )
        self.employee2 = Employee.objects.create_user(
            username='emp_bob', email='bob@scoring.com', password='password123',
            company=self.company, role=EmployeeRole.EMPLOYEE,
            org_unit=self.dept_unit, position=self.position, manager=None,
        )
        self.other_emp = Employee.objects.create_user(
            username='other_emp', email='other@other.com', password='password123',
            company=self.other_company, role=EmployeeRole.EMPLOYEE,
        )

        self.category = KpiCategory.objects.create(company=self.company, name='Operations KPIs')

        self.cycle = PerformanceCycle.objects.create(
            company=self.company, name='2026 Q1 Cycle',
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
        )

        self.client = APIClient()

    def test_directional_raw_scoring_mathematics(self):
        """
        Verify mathematical correctness across HIGHER_IS_BETTER, LOWER_IS_BETTER,
        TARGET_BASED, BOOLEAN, and RATING directions.
        """
        # 1. HIGHER_IS_BETTER
        score = KpiScoringService.calculate_raw_score(
            measurement_type=KpiTemplate.MeasurementType.PERCENT,
            direction=KpiTemplate.Direction.HIGHER_IS_BETTER,
            target='100', actual_value='90',
        )
        self.assertEqual(score, Decimal('90.00'))

        score_over = KpiScoringService.calculate_raw_score(
            measurement_type=KpiTemplate.MeasurementType.NUMERIC,
            direction=KpiTemplate.Direction.HIGHER_IS_BETTER,
            target='100', actual_value='125',
        )
        self.assertEqual(score_over, Decimal('125.00'))

        # 2. LOWER_IS_BETTER (e.g. latency, error rate)
        # Half the latency (100ms vs 200ms target) is 200% achievement
        score_lower_better = KpiScoringService.calculate_raw_score(
            measurement_type=KpiTemplate.MeasurementType.TIME,
            direction=KpiTemplate.Direction.LOWER_IS_BETTER,
            target='200', actual_value='100',
        )
        self.assertEqual(score_lower_better, Decimal('200.00'))

        # Double the latency (400ms vs 200ms target) is 50% achievement
        score_lower_worse = KpiScoringService.calculate_raw_score(
            measurement_type=KpiTemplate.MeasurementType.TIME,
            direction=KpiTemplate.Direction.LOWER_IS_BETTER,
            target='200', actual_value='400',
        )
        self.assertEqual(score_lower_worse, Decimal('50.00'))

        # 3. TARGET_BASED (deviation penalised)
        score_target_exact = KpiScoringService.calculate_raw_score(
            measurement_type=KpiTemplate.MeasurementType.NUMERIC,
            direction=KpiTemplate.Direction.TARGET_BASED,
            target='100', actual_value='100',
        )
        self.assertEqual(score_target_exact, Decimal('100.00'))

        score_target_dev = KpiScoringService.calculate_raw_score(
            measurement_type=KpiTemplate.MeasurementType.NUMERIC,
            direction=KpiTemplate.Direction.TARGET_BASED,
            target='100', actual_value='95',
        )
        self.assertEqual(score_target_dev, Decimal('95.00'))

        score_target_over = KpiScoringService.calculate_raw_score(
            measurement_type=KpiTemplate.MeasurementType.NUMERIC,
            direction=KpiTemplate.Direction.TARGET_BASED,
            target='100', actual_value='105',
        )
        self.assertEqual(score_target_over, Decimal('95.00'))

        # 4. BOOLEAN
        self.assertEqual(
            KpiScoringService.calculate_raw_score(
                measurement_type=KpiTemplate.MeasurementType.BOOLEAN,
                direction=KpiTemplate.Direction.HIGHER_IS_BETTER,
                target='1', actual_value='true',
            ),
            Decimal('100.00'),
        )
        self.assertEqual(
            KpiScoringService.calculate_raw_score(
                measurement_type=KpiTemplate.MeasurementType.BOOLEAN,
                direction=KpiTemplate.Direction.HIGHER_IS_BETTER,
                target='1', actual_value='false',
            ),
            Decimal('0.00'),
        )

        # 5. RATING (Target based: 4.5 / 5.0 -> 90%)
        score_rating = KpiScoringService.calculate_raw_score(
            measurement_type=KpiTemplate.MeasurementType.RATING,
            direction=KpiTemplate.Direction.HIGHER_IS_BETTER,
            target='5.0', actual_value='4.5',
        )
        self.assertEqual(score_rating, Decimal('90.00'))

    def test_score_normalization_and_clamping(self):
        """
        Verify clamping to [min_score, max_score] boundary constraints.
        """
        # Standard default cap at 100.00
        norm_capped = KpiScoringService.normalize_score(
            raw_score=Decimal('135.50'), min_score=Decimal('0'), max_score=Decimal('100'),
        )
        self.assertEqual(norm_capped, Decimal('100.00'))

        # Custom over-achievement cap at 120.00
        norm_custom_cap = KpiScoringService.normalize_score(
            raw_score=Decimal('135.50'), min_score=Decimal('0'), max_score=Decimal('120'),
        )
        self.assertEqual(norm_custom_cap, Decimal('120.00'))

        # Min score clamping at 0.00
        norm_negative = KpiScoringService.normalize_score(
            raw_score=Decimal('-15.00'), min_score=Decimal('0'), max_score=Decimal('100'),
        )
        self.assertEqual(norm_negative, Decimal('0.00'))

    def test_weighted_contribution_blueprint_example(self):
        """
        Verify blueprint worked example:
        Raw Score = 90, Weight = 30% -> Weighted Contribution = 27.00
        """
        contrib = KpiScoringService.calculate_weighted_contribution(
            normalized_score=Decimal('90.00'), weight=Decimal('30.00'),
        )
        self.assertEqual(contrib, Decimal('27.00'))

    def test_cycle_score_aggregation_and_evaluation(self):
        """
        Verify multi-KPI cycle aggregation:
        KPI 1: Raw 90, Weight 30% -> 27.00
        KPI 2: Raw 120, Capped 100, Weight 50% -> 50.00
        KPI 3: Raw 100, Weight 20% -> 20.00
        Overall Score = 27.00 + 50.00 + 20.00 = 97.00
        """
        tmpl1 = KpiTemplate.objects.create(
            company=self.company, name='Task Execution', category=self.category,
            measurement_type=KpiTemplate.MeasurementType.PERCENT,
            direction=KpiTemplate.Direction.HIGHER_IS_BETTER,
            default_target='100', default_weight=30, min_score=0, max_score=100,
        )
        tmpl2 = KpiTemplate.objects.create(
            company=self.company, name='Incident Resolution Speed', category=self.category,
            measurement_type=KpiTemplate.MeasurementType.NUMERIC,
            direction=KpiTemplate.Direction.HIGHER_IS_BETTER,
            default_target='100', default_weight=50, min_score=0, max_score=100,
        )
        tmpl3 = KpiTemplate.objects.create(
            company=self.company, name='Safety Compliance', category=self.category,
            measurement_type=KpiTemplate.MeasurementType.BOOLEAN,
            direction=KpiTemplate.Direction.HIGHER_IS_BETTER,
            default_target='1', default_weight=20, min_score=0, max_score=100,
        )

        fw = KpiFramework.objects.create(
            company=self.company, name='Ops Standards',
            scope_type=KpiFramework.ScopeType.GLOBAL, status=KpiFramework.Status.PUBLISHED,
        )
        KpiFrameworkItem.objects.create(framework=fw, template=tmpl1, weight=30, target='100')
        KpiFrameworkItem.objects.create(framework=fw, template=tmpl2, weight=50, target='100')
        KpiFrameworkItem.objects.create(framework=fw, template=tmpl3, weight=20, target='1')

        # Generate cycle assignments (4 active company employees * 3 KPIs = 12 assignments)
        assignments = KpiAssignmentService.generate_assignments_for_cycle(self.cycle)
        self.assertEqual(len(assignments), 12)

        a1 = EmployeeKpiAssignment.objects.get(cycle=self.cycle, employee=self.employee1, template=tmpl1)
        a2 = EmployeeKpiAssignment.objects.get(cycle=self.cycle, employee=self.employee1, template=tmpl2)
        a3 = EmployeeKpiAssignment.objects.get(cycle=self.cycle, employee=self.employee1, template=tmpl3)

        # Record measurements
        KpiMeasurement.objects.create(company=self.company, assignment=a1, value='90', recorded_by=self.manager)
        KpiMeasurement.objects.create(company=self.company, assignment=a2, value='120', recorded_by=self.manager)
        KpiMeasurement.objects.create(company=self.company, assignment=a3, value='true', recorded_by=self.manager)

        # Evaluate cycle for Alice
        summary = KpiScoringService.evaluate_cycle_for_employee(self.cycle, self.employee1)

        self.assertEqual(summary['total_assignments'], 3)
        self.assertEqual(summary['measured_assignments'], 3)
        self.assertEqual(summary['completion_rate_percent'], 100.0)
        self.assertEqual(summary['total_performance_score'], 97.00)

    def test_score_summary_api_endpoint(self):
        """
        Verify /api/performance-cycles/{uuid}/score_summary/ with permissions.
        """
        tmpl = KpiTemplate.objects.create(
            company=self.company, name='General SLA', category=self.category,
            measurement_type=KpiTemplate.MeasurementType.PERCENT,
            direction=KpiTemplate.Direction.HIGHER_IS_BETTER,
            default_target='100', default_weight=100, min_score=0, max_score=100,
        )
        fw = KpiFramework.objects.create(
            company=self.company, name='General FW',
            scope_type=KpiFramework.ScopeType.GLOBAL, status=KpiFramework.Status.PUBLISHED,
        )
        KpiFrameworkItem.objects.create(framework=fw, template=tmpl, weight=100, target='100')
        KpiAssignmentService.generate_assignments_for_cycle(self.cycle)

        a = EmployeeKpiAssignment.objects.get(cycle=self.cycle, employee=self.employee1, template=tmpl)
        KpiMeasurement.objects.create(company=self.company, assignment=a, value='95', recorded_by=self.manager)

        url = f'/api/performance-cycles/{self.cycle.uuid}/score_summary/'

        # 1. Employee Alice querying own score -> 200 OK
        self.client.force_authenticate(user=self.employee1)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['total_performance_score'], 95.0)

        # 2. Employee Alice querying Bob's score -> 403 Forbidden
        resp_bob = self.client.get(f'{url}?employee_uuid={self.employee2.uuid}')
        self.assertEqual(resp_bob.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Manager querying Alice (direct report) -> 200 OK
        self.client.force_authenticate(user=self.manager)
        resp_mgr = self.client.get(f'{url}?employee_uuid={self.employee1.uuid}')
        self.assertEqual(resp_mgr.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_mgr.data['total_performance_score'], 95.0)

        # 4. HR querying company overview -> 200 OK
        self.client.force_authenticate(user=self.hr)
        resp_hr = self.client.get(url)
        self.assertEqual(resp_hr.status_code, status.HTTP_200_OK)
        self.assertIn('employees', resp_hr.data)

        # 5. Cross-company employee lookup -> 404
        resp_other = self.client.get(f'{url}?employee_uuid={self.other_emp.uuid}')
        self.assertEqual(resp_other.status_code, status.HTTP_404_NOT_FOUND)
