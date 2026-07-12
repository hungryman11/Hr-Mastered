from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.api.views import CompanyViewSet, DepartmentViewSet, EmployeeViewSet, LeaveBalanceViewSet, LeaveRequestViewSet, LeaveTypeViewSet, OrgUnitViewSet

router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'org-units', OrgUnitViewSet, basename='org-unit')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'leave-types', LeaveTypeViewSet, basename='leave-type')
router.register(r'leave-balances', LeaveBalanceViewSet, basename='leave-balance')
router.register(r'leave-requests', LeaveRequestViewSet, basename='leave-request')

urlpatterns = [
    path('', include(router.urls)),
]
