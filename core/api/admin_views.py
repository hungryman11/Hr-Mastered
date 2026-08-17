"""
Admin/HR dashboard API views and serializers.

Provides aggregated data and summary statistics for org admins and HR admins.
"""
from django.db.models import Q, Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import (
    Company, Employee, EmployeeRole, Department, OrgUnit, Position,
    LeaveRequest, PayrollRun
)
from core.permissions import IsHRAdmin


class AdminDashboardViewSet(viewsets.ViewSet):
    """
    Admin dashboard API providing org/company-wide statistics and summary data.
    
    Only accessible to HR Admins and Org Admins.
    """
    permission_classes = [IsHRAdmin]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get dashboard summary statistics for the authenticated admin's company.
        
        Returns:
        - total_employees: count of all active employees
        - inactive_employees: count of inactive employees
        - employees_by_role: breakdown by role
        - pending_onboarding: count with PENDING status
        - departments: count of departments
        - org_units: count of org units
        - positions: count of positions
        - pending_leave_requests: count of leave requests awaiting approval
        - payroll_runs_in_progress: count of open payroll runs
        """
        user = request.user
        if not user or not user.is_authenticated or not hasattr(user, 'company'):
            return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        company = user.company
        if not company:
            return Response({'detail': 'User does not belong to a company'}, status=status.HTTP_403_FORBIDDEN)

        # Employee counts
        employee_queryset = Employee.objects.filter(company=company)
        total_active = employee_queryset.filter(is_active=True).count()
        total_inactive = employee_queryset.filter(is_active=False).count()
        
        # Breakdown by role
        employees_by_role = employee_queryset.values('role').annotate(count=Count('id')).order_by('role')
        role_breakdown = {item['role']: item['count'] for item in employees_by_role}
        
        # Onboarding status
        pending_onboarding = employee_queryset.filter(onboarding_status='PENDING').count()
        
        # Organization structure
        dept_count = Department.objects.filter(company=company).count()
        unit_count = OrgUnit.objects.filter(company=company).count()
        pos_count = Position.objects.filter(company=company).count()
        
        # Leave requests awaiting approval
        pending_leave = LeaveRequest.objects.filter(
            company=company,
            status__in=['PENDING', 'APPROVED_BY_FIRST']
        ).count()
        
        # Payroll runs in progress
        payroll_in_progress = PayrollRun.objects.filter(
            company=company,
            status__in=['OPEN', 'EXPORTED']
        ).count()
        
        return Response({
            'total_active_employees': total_active,
            'total_inactive_employees': total_inactive,
            'employees_by_role': role_breakdown,
            'pending_onboarding': pending_onboarding,
            'departments': dept_count,
            'org_units': unit_count,
            'positions': pos_count,
            'pending_leave_requests': pending_leave,
            'payroll_runs_in_progress': payroll_in_progress,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def recent_employees(self, request):
        """
        Get list of recently created employees (last 10).
        
        Returns:
        - id, uuid, first_name, last_name, email, role, onboarding_status, created_at
        """
        user = request.user
        if not user or not user.is_authenticated or not hasattr(user, 'company'):
            return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        company = user.company
        if not company:
            return Response({'detail': 'User does not belong to a company'}, status=status.HTTP_403_FORBIDDEN)

        from core.serializers import EmployeeSerializer
        
        recent = Employee.objects.filter(company=company).order_by('-created_at')[:10]
        serializer = EmployeeSerializer(recent, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def employee_stats(self, request):
        """
        Get detailed employee statistics by department and role.
        
        Returns breakdown of active/inactive employees by department.
        """
        user = request.user
        if not user or not user.is_authenticated or not hasattr(user, 'company'):
            return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        company = user.company
        if not company:
            return Response({'detail': 'User does not belong to a company'}, status=status.HTTP_403_FORBIDDEN)

        # Employees by department
        dept_stats = []
        departments = Department.objects.filter(company=company)
        
        for dept in departments:
            active = Employee.objects.filter(
                company=company,
                department=dept,
                is_active=True
            ).count()
            inactive = Employee.objects.filter(
                company=company,
                department=dept,
                is_active=False
            ).count()
            dept_stats.append({
                'department_id': dept.id,
                'department_name': dept.name,
                'active_count': active,
                'inactive_count': inactive,
                'total': active + inactive,
            })
        
        return Response(dept_stats, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def organization_structure(self, request):
        """
        Get organization structure overview: org units and positions.
        
        Returns:
        - org_units: list with count of employees per unit
        - positions: list with count of employees per position
        """
        user = request.user
        if not user or not user.is_authenticated or not hasattr(user, 'company'):
            return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        company = user.company
        if not company:
            return Response({'detail': 'User does not belong to a company'}, status=status.HTTP_403_FORBIDDEN)

        # Org units
        org_units_data = []
        org_units = OrgUnit.objects.filter(company=company)
        for unit in org_units:
            emp_count = Employee.objects.filter(
                company=company,
                org_unit=unit,
                is_active=True
            ).count()
            org_units_data.append({
                'id': unit.id,
                'name': unit.name,
                'type': unit.unit_type,
                'employee_count': emp_count,
            })
        
        # Positions
        positions_data = []
        positions = Position.objects.filter(company=company, active=True)
        for pos in positions:
            emp_count = Employee.objects.filter(
                company=company,
                position=pos,
                is_active=True
            ).count()
            positions_data.append({
                'id': pos.id,
                'title': pos.title,
                'org_unit_id': pos.org_unit_id,
                'employee_count': emp_count,
            })
        
        return Response({
            'org_units': org_units_data,
            'positions': positions_data,
        }, status=status.HTTP_200_OK)
