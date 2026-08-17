from decimal import Decimal
from datetime import date
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Company, Employee, EmployeeRole, OrgUnit, Position,
    KpiCategory, KpiTemplate, KpiFramework, KpiFrameworkItem,
    PerformanceCycle, EmployeeKpiAssignment, KpiMeasurement,
    PerformanceReview,
)
from core.kpi_service import KpiAssignmentService


@override_settings(ZOHO_USE_MOCK=True)
class PerformanceReviewTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Review Co')
        self.other_company = Company.objects.create(name='Other Co')

        self.hr = Employee.objects.create_user(
            username='hr_rev', email='hr@review.com', password='password123',
            company=self.company, role=EmployeeRole.HR_ADMIN,
        )
        self.manager = Employee.objects.create_user(
            username='mgr_rev', email='mgr@review.com', password='password123',
            company=self.company, role=EmployeeRole.MANAGER,
        )
        self.dept_unit = OrgUnit.objects.create(
            company=self.company, name='Engineering',
            unit_type=OrgUnit.UnitType.DEPARTMENT, head=self.manager,
        )
        self.position = Position.objects.create(
            company=self.company, org_unit=self.dept_unit,
            title='Software Engineer', code='SWE-01',
        )
        self.employee1 = Employee.objects.create_user(
            username='emp_alice', email='alice@review.com', password='password123',
            company=self.company, role=EmployeeRole.EMPLOYEE,
            org_unit=self.dept_unit, position=self.position, manager=self.manager,
        )
        self.employee2 = Employee.objects.create_user(
            username='emp_bob', email='bob@review.com', password='password123',
            company=self.company, role=EmployeeRole.EMPLOYEE,
            org_unit=self.dept_unit, position=self.position, manager=None,
        )
        self.other_emp = Employee.objects.create_user(
            username='other_emp', email='other@other.com', password='password123',
            company=self.other_company, role=EmployeeRole.EMPLOYEE,
        )

        self.category = KpiCategory.objects.create(company=self.company, name='Engineering KPIs')

        self.cycle = PerformanceCycle.objects.create(
            company=self.company, name='2026 Q1 Cycle',
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
        )

        # Setup KPI and generate assignments
        self.template = KpiTemplate.objects.create(
            company=self.company, name='Code Quality', category=self.category,
            measurement_type=KpiTemplate.MeasurementType.PERCENT,
            direction=KpiTemplate.Direction.HIGHER_IS_BETTER,
            default_target='100', default_weight=100, min_score=0, max_score=100,
        )
        fw = KpiFramework.objects.create(
            company=self.company, name='Engineering Framework',
            scope_type=KpiFramework.ScopeType.GLOBAL, status=KpiFramework.Status.PUBLISHED,
        )
        KpiFrameworkItem.objects.create(framework=fw, template=self.template, weight=100, target='100')
        KpiAssignmentService.generate_assignments_for_cycle(self.cycle)

        # Record measurement for Alice
        a1 = EmployeeKpiAssignment.objects.get(cycle=self.cycle, employee=self.employee1, template=self.template)
        KpiMeasurement.objects.create(company=self.company, assignment=a1, value='90', recorded_by=self.manager)

        self.client = APIClient()

    def test_initialize_cycle_reviews_action(self):
        """
        HR Admin initializes performance reviews for all active employees in a cycle.
        """
        self.client.force_authenticate(user=self.hr)
        url = '/api/performance-reviews/initialize_cycle_reviews/'
        resp = self.client.post(url, {'cycle_uuid': str(self.cycle.uuid)}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # 4 active employees in company
        self.assertEqual(len(resp.data), 4)

        alice_review = PerformanceReview.objects.get(cycle=self.cycle, employee=self.employee1)
        self.assertEqual(alice_review.system_score, Decimal('90.00'))
        self.assertEqual(alice_review.reviewer, self.manager)
        self.assertEqual(alice_review.status, PerformanceReview.Status.DRAFT)

    def test_performance_review_full_lifecycle(self):
        """
        Walkthrough full review workflow:
        1. DRAFT initialized
        2. Employee submits self-assessment -> SUBMITTED
        3. Manager submits review -> MANAGER_REVIEWED
        4. HR submits calibration -> CALIBRATED
        5. Finalize -> FINALIZED (immutable)
        """
        review = PerformanceReview.objects.create(
            company=self.company, cycle=self.cycle, employee=self.employee1,
            reviewer=self.manager, system_score=Decimal('90.00'),
            status=PerformanceReview.Status.DRAFT,
        )
        url = f'/api/performance-reviews/{review.uuid}/'

        # 1. Alice submits self-assessment
        self.client.force_authenticate(user=self.employee1)
        resp_self = self.client.post(f'{url}self_assessment/', {
            'employee_self_score': '92.50',
            'employee_comments': 'Delivered all features on time.',
        }, format='json')
        self.assertEqual(resp_self.status_code, status.HTTP_200_OK)
        review.refresh_from_db()
        self.assertEqual(review.status, PerformanceReview.Status.SUBMITTED)
        self.assertEqual(review.employee_self_score, Decimal('92.50'))

        # 2. Manager submits manager review
        self.client.force_authenticate(user=self.manager)
        resp_mgr = self.client.post(f'{url}manager_review/', {
            'manager_score': '88.00',
            'manager_comments': 'Strong technical output, improve code review turnaround.',
        }, format='json')
        self.assertEqual(resp_mgr.status_code, status.HTTP_200_OK)
        review.refresh_from_db()
        self.assertEqual(review.status, PerformanceReview.Status.MANAGER_REVIEWED)
        self.assertEqual(review.manager_score, Decimal('88.00'))

        # 3. HR performs the required HR review.
        self.client.force_authenticate(user=self.hr)
        resp_hr = self.client.post(f'{url}hr_review/', {
            'hr_score': '90.00',
            'hr_comments': 'Confirmed evidence and manager assessment.',
        }, format='json')
        self.assertEqual(resp_hr.status_code, status.HTTP_200_OK)
        review.refresh_from_db()
        self.assertEqual(review.status, PerformanceReview.Status.HR_REVIEWED)

        # 4. HR calibrates score
        resp_cal = self.client.post(f'{url}calibrate/', {
            'calibrated_score': '90.00',
            'reason': 'Adjusted based on cross-engineering bell curve alignment.',
        }, format='json')
        self.assertEqual(resp_cal.status_code, status.HTTP_200_OK)
        review.refresh_from_db()
        self.assertEqual(review.status, PerformanceReview.Status.CALIBRATED)
        self.assertEqual(review.calibrated_score, Decimal('90.00'))
        self.assertEqual(review.calibrated_by, self.hr)
        self.assertIsNotNone(review.calibrated_at)

        # 5. HR finalizes review
        resp_fin = self.client.post(f'{url}finalize/', {
            'final_comments': 'Final calibrated rating confirmed.',
        }, format='json')
        self.assertEqual(resp_fin.status_code, status.HTTP_200_OK)
        review.refresh_from_db()
        self.assertEqual(review.status, PerformanceReview.Status.FINALIZED)
        self.assertEqual(review.final_score, Decimal('90.00'))
        self.assertEqual(review.finalized_by, self.hr)
        self.assertIsNotNone(review.finalized_at)

    def test_actions_cannot_skip_the_review_state_machine(self):
        review = PerformanceReview.objects.create(
            company=self.company, cycle=self.cycle, employee=self.employee1,
            reviewer=self.manager, status=PerformanceReview.Status.DRAFT,
        )
        base_url = f'/api/performance-reviews/{review.uuid}/'

        self.client.force_authenticate(user=self.hr)
        self.assertEqual(
            self.client.post(f'{base_url}finalize/', format='json').status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.post(f'{base_url}calibrate/', {'calibrated_score': '90'}, format='json').status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.client.force_authenticate(user=self.manager)
        self.assertEqual(
            self.client.post(f'{base_url}manager_review/', {'manager_score': '90'}, format='json').status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_finalized_review_immutability(self):
        """
        Verify that once FINALIZED, review cannot be modified or deleted via ORM or API.
        """
        review = PerformanceReview.objects.create(
            company=self.company, cycle=self.cycle, employee=self.employee1,
            reviewer=self.manager, system_score=Decimal('90.00'),
            final_score=Decimal('90.00'), status=PerformanceReview.Status.FINALIZED,
        )

        # 1. ORM modification attempt -> ValidationError
        review.final_comments = 'Attempting illegal update'
        with self.assertRaises(ValidationError):
            review.save()

        # 2. ORM deletion attempt -> ValidationError
        with self.assertRaises(ValidationError):
            review.delete()

        # 3. API modification attempt -> 400 Bad Request
        self.client.force_authenticate(user=self.hr)
        resp = self.client.post(f'/api/performance-reviews/{review.uuid}/calibrate/', {
            'calibrated_score': '99.00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_role_based_permissions_and_scoping(self):
        """
        Verify review queryset visibility and action permissions across roles.
        """
        rev1 = PerformanceReview.objects.create(
            company=self.company, cycle=self.cycle, employee=self.employee1,
            reviewer=self.manager, status=PerformanceReview.Status.DRAFT,
        )
        rev2 = PerformanceReview.objects.create(
            company=self.company, cycle=self.cycle, employee=self.employee2,
            status=PerformanceReview.Status.DRAFT,
        )

        # Employee Alice can only see own review
        self.client.force_authenticate(user=self.employee1)
        resp_alice = self.client.get('/api/performance-reviews/')
        self.assertEqual(resp_alice.status_code, status.HTTP_200_OK)
        uuids = [r['uuid'] for r in resp_alice.data['results']] if 'results' in resp_alice.data else [r['uuid'] for r in resp_alice.data]
        self.assertIn(str(rev1.uuid), uuids)
        self.assertNotIn(str(rev2.uuid), uuids)

        # Employee Alice cannot submit self-assessment for Bob (not in Alice's scoped queryset -> 404)
        resp_bob_self = self.client.post(f'/api/performance-reviews/{rev2.uuid}/self_assessment/', {
            'employee_self_score': '100',
        }, format='json')
        self.assertEqual(resp_bob_self.status_code, status.HTTP_404_NOT_FOUND)

        # Employee Alice cannot calibrate
        resp_cal_unauth = self.client.post(f'/api/performance-reviews/{rev1.uuid}/calibrate/', {
            'calibrated_score': '95',
        }, format='json')
        self.assertEqual(resp_cal_unauth.status_code, status.HTTP_403_FORBIDDEN)

        # Cross-company user cannot see reviews
        self.client.force_authenticate(user=self.other_emp)
        resp_other = self.client.get(f'/api/performance-reviews/{rev1.uuid}/')
        self.assertEqual(resp_other.status_code, status.HTTP_404_NOT_FOUND)
