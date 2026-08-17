from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Company, Employee, EmployeeRole, KpiCategory, KpiTemplate, KpiFramework, PerformanceCycle, EmployeeKpiAssignment

class SecurityTenantIsolationTests(TestCase):
    def setUp(self):
        # Company A
        self.company_a = Company.objects.create(name='Company A')
        self.hr_a = Employee.objects.create_user(
            username='hr_a', email='hr@comp-a.com', password='pass',
            company=self.company_a, role=EmployeeRole.HR_ADMIN
        )
        self.mgr_a = Employee.objects.create_user(
            username='mgr_a', email='mgr@comp-a.com', password='pass',
            company=self.company_a, role=EmployeeRole.MANAGER
        )
        self.emp_a1 = Employee.objects.create_user(
            username='emp_a1', email='emp1@comp-a.com', password='pass',
            company=self.company_a, role=EmployeeRole.EMPLOYEE, manager=self.mgr_a
        )
        self.emp_a2 = Employee.objects.create_user(
            username='emp_a2', email='emp2@comp-a.com', password='pass',
            company=self.company_a, role=EmployeeRole.EMPLOYEE
        )

        # Company B
        self.company_b = Company.objects.create(name='Company B')
        self.hr_b = Employee.objects.create_user(
            username='hr_b', email='hr@comp-b.com', password='pass',
            company=self.company_b, role=EmployeeRole.HR_ADMIN
        )
        self.emp_b = Employee.objects.create_user(
            username='emp_b', email='emp@comp-b.com', password='pass',
            company=self.company_b, role=EmployeeRole.EMPLOYEE
        )

        self.client = APIClient()

    def test_non_hr_cannot_create_kpi_category(self):
        self.client.force_authenticate(user=self.emp_a1)
        res = self.client.post('/api/kpi-categories/', {'name': 'Unauthorized Cat'})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.hr_a)
        res_hr = self.client.post('/api/kpi-categories/', {'name': 'HR Cat'})
        self.assertEqual(res_hr.status_code, status.HTTP_201_CREATED)

    def test_non_hr_cannot_create_kpi_template(self):
        self.client.force_authenticate(user=self.emp_a1)
        res = self.client.post('/api/kpi-templates/', {'name': 'Unauthorized Temp'})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.hr_a)
        res_hr = self.client.post('/api/kpi-templates/', {'name': 'HR Temp'})
        self.assertEqual(res_hr.status_code, status.HTTP_201_CREATED)

    def test_non_hr_cannot_create_performance_cycle(self):
        self.client.force_authenticate(user=self.emp_a1)
        res = self.client.post('/api/performance-cycles/', {'name': 'Cycle 2026', 'start_date': '2026-01-01', 'end_date': '2026-12-31'})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.hr_a)
        res_hr = self.client.post('/api/performance-cycles/', {'name': 'Cycle 2026', 'start_date': '2026-01-01', 'end_date': '2026-12-31'})
        self.assertEqual(res_hr.status_code, status.HTTP_201_CREATED)

    def test_non_hr_cannot_generate_assignments(self):
        cycle = PerformanceCycle.objects.create(company=self.company_a, name='Cycle A', start_date='2026-01-01', end_date='2026-12-31')
        self.client.force_authenticate(user=self.emp_a1)
        res = self.client.post(f'/api/performance-cycles/{cycle.uuid}/generate_assignments/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_cross_company_isolation(self):
        cat_b = KpiCategory.objects.create(company=self.company_b, name='Cat B')
        self.client.force_authenticate(user=self.hr_a)
        res = self.client.get(f'/api/kpi-categories/{cat_b.uuid}/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_assignment_visibility_scoping(self):
        cycle = PerformanceCycle.objects.create(company=self.company_a, name='Cycle A', start_date='2026-01-01', end_date='2026-12-31')
        tmpl = KpiTemplate.objects.create(company=self.company_a, name='Tmpl')

        assign_emp1 = EmployeeKpiAssignment.objects.create(
            company=self.company_a, cycle=cycle, employee=self.emp_a1, template=tmpl, weight=50
        )
        assign_emp2 = EmployeeKpiAssignment.objects.create(
            company=self.company_a, cycle=cycle, employee=self.emp_a2, template=tmpl, weight=50
        )

        # Employee 1 should only see their assignment
        self.client.force_authenticate(user=self.emp_a1)
        res1 = self.client.get('/api/kpi-assignments/')
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        uuids1 = [item['uuid'] for item in res1.data]
        self.assertIn(str(assign_emp1.uuid), uuids1)
        self.assertNotIn(str(assign_emp2.uuid), uuids1)

        # Manager of Employee 1 should see Employee 1's assignment
        self.client.force_authenticate(user=self.mgr_a)
        res_mgr = self.client.get('/api/kpi-assignments/')
        self.assertEqual(res_mgr.status_code, status.HTTP_200_OK)
        uuids_mgr = [item['uuid'] for item in res_mgr.data]
        self.assertIn(str(assign_emp1.uuid), uuids_mgr)
        self.assertNotIn(str(assign_emp2.uuid), uuids_mgr)

        # HR Admin should see both assignments
        self.client.force_authenticate(user=self.hr_a)
        res_hr = self.client.get('/api/kpi-assignments/')
        self.assertEqual(res_hr.status_code, status.HTTP_200_OK)
        uuids_hr = [item['uuid'] for item in res_hr.data]
        self.assertIn(str(assign_emp1.uuid), uuids_hr)
        self.assertIn(str(assign_emp2.uuid), uuids_hr)
