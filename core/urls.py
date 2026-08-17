from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.api.views import (
    ApprovalDecisionViewSet, ApprovalDocumentViewSet,
    CompanyHolidayViewSet, CompanyWorkCalendarViewSet,
    CompanyViewSet, DeliveryJobViewSet, DepartmentViewSet,
    EmployeeViewSet, LeaveBalanceViewSet, LeaveRequestViewSet,
    LeaveTypeViewSet, OrgUnitViewSet, PositionViewSet,
)
from core.api.admin_views import AdminDashboardViewSet
from core.api.payroll_views import (
    PayrollAdjustmentViewSet, PayrollDeductionViewSet,
    PayrollProfileViewSet, PayrollRunViewSet, StatutoryRuleViewSet,
)
from core.api.kpi_views import (
    KpiCategoryViewSet, KpiTemplateViewSet, KpiFrameworkViewSet,
    KpiFrameworkItemViewSet, EmployeeKpiOverrideViewSet,
    PerformanceCycleViewSet, EmployeeKpiAssignmentViewSet,
    KpiMeasurementViewSet, PerformanceReviewViewSet,
)
from core.api.salary_views import SalaryRecordViewSet
from core.api.demo_auth import demo_login, demo_login_users

router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'org-units', OrgUnitViewSet, basename='org-unit')
router.register(r'positions', PositionViewSet, basename='position')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'leave-types', LeaveTypeViewSet, basename='leave-type')
router.register(r'leave-balances', LeaveBalanceViewSet, basename='leave-balance')
router.register(r'holidays', CompanyHolidayViewSet, basename='holiday')
router.register(r'work-calendars', CompanyWorkCalendarViewSet, basename='work-calendar')
router.register(r'leave-requests', LeaveRequestViewSet, basename='leave-request')
router.register(r'approval-decisions', ApprovalDecisionViewSet, basename='approval-decision')
router.register(r'approval-documents', ApprovalDocumentViewSet, basename='approval-document')
router.register(r'delivery-jobs', DeliveryJobViewSet, basename='delivery-job')
router.register(r'payroll-profiles', PayrollProfileViewSet, basename='payroll-profile')
router.register(r'payroll-runs', PayrollRunViewSet, basename='payroll-run')
router.register(r'payroll-adjustments', PayrollAdjustmentViewSet, basename='payroll-adjustment')
router.register(r'statutory-rules', StatutoryRuleViewSet, basename='statutory-rule')
router.register(r'payroll-deductions', PayrollDeductionViewSet, basename='payroll-deduction')
router.register(r'kpi-categories', KpiCategoryViewSet, basename='kpi-category')
router.register(r'kpi-templates', KpiTemplateViewSet, basename='kpi-template')
router.register(r'kpi-frameworks', KpiFrameworkViewSet, basename='kpi-framework')
router.register(r'kpi-framework-items', KpiFrameworkItemViewSet, basename='kpi-framework-item')
router.register(r'kpi-employee-overrides', EmployeeKpiOverrideViewSet, basename='kpi-employee-override')
router.register(r'performance-cycles', PerformanceCycleViewSet, basename='performance-cycle')
router.register(r'kpi-assignments', EmployeeKpiAssignmentViewSet, basename='kpi-assignment')
router.register(r'kpi-measurements', KpiMeasurementViewSet, basename='kpi-measurement')
router.register(r'performance-reviews', PerformanceReviewViewSet, basename='performance-review')
router.register(r'salary-records', SalaryRecordViewSet, basename='salary-record')
router.register(r'admin-dashboard', AdminDashboardViewSet, basename='admin-dashboard')

urlpatterns = [
    path('demo-auth/users/', demo_login_users, name='demo-login-users'),
    path('demo-auth/login/', demo_login, name='demo-login'),
    path('', include(router.urls)),
]
