from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import ApprovalDocument, Company, Department, Employee, LeaveBalance, LeaveRequest, LeaveType, OrgUnit
from core.onboarding import ApprovalRoutingService, LeaveService, OnboardingService
from core.permissions import IsCompanyMember, IsHRAdmin
from core.serializers import CompanySerializer, DepartmentSerializer, EmployeeSerializer, OrgUnitSerializer
from core.leave_serializers import ApprovalDocumentSerializer, LeaveBalanceSerializer, LeaveRequestSerializer, LeaveTypeSerializer


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    lookup_field = 'uuid'
    permission_classes = [IsHRAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Company.objects.all()
        return Company.objects.filter(pk=getattr(user.company, 'pk', None))


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_queryset(self):
        user = self.request.user
        queryset = Department.objects.select_related('company')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)


class OrgUnitViewSet(viewsets.ModelViewSet):
    serializer_class = OrgUnitSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_queryset(self):
        user = self.request.user
        queryset = OrgUnit.objects.select_related('company', 'parent', 'head')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_queryset(self):
        user = self.request.user
        queryset = Employee.objects.select_related('company', 'department', 'org_unit', 'manager')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)

    @action(detail=True, methods=['post'], permission_classes=[IsHRAdmin])
    def onboard(self, request, uuid=None):
        employee = self.get_object()
        try:
            folder = OnboardingService.onboard_employee(employee, created_by=request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'employee': EmployeeSerializer(employee, context={'request': request}).data,
            'workdrive_folder_uuid': str(folder.uuid),
            'workdrive_folder_id': folder.zoho_folder_id,
        }, status=status.HTTP_200_OK)


class LeaveTypeViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveTypeSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_queryset(self):
        user = self.request.user
        queryset = LeaveType.objects.select_related('company')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveBalanceSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_queryset(self):
        user = self.request.user
        queryset = LeaveBalance.objects.select_related('company', 'employee', 'leave_type')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)


class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_queryset(self):
        user = self.request.user
        queryset = LeaveRequest.objects.select_related('company', 'employee', 'leave_type', 'reviewed_by')
        if user.is_superuser:
            return queryset
        if user.role in {'HR_ADMIN', 'MANAGER'}:
            return queryset.filter(company=user.company)
        return queryset.filter(company=user.company, employee=user)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, employee=self.request.user, created_by=self.request.user, updated_by=self.request.user)

    @action(detail=True, methods=['get'])
    def routing(self, request, uuid=None):
        leave_request = self.get_object()
        approvers = ApprovalRoutingService.get_leave_approvers(leave_request.employee)
        return Response({
            'next_approver': EmployeeSerializer(approvers[0], context={'request': request}).data if approvers else None,
            'approvers': EmployeeSerializer(approvers, many=True, context={'request': request}).data,
        })

    @action(detail=True, methods=['post'])
    def approve(self, request, uuid=None):
        leave_request = self.get_object()
        if request.user.role not in {'HR_ADMIN', 'MANAGER'}:
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            LeaveService.approve_leave(leave_request, reviewed_by=request.user)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(leave_request).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, uuid=None):
        leave_request = self.get_object()
        if request.user.role not in {'HR_ADMIN', 'MANAGER'}:
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
        reason = request.data.get('reason', '')
        try:
            LeaveService.reject_leave(leave_request, reviewed_by=request.user, reason=reason)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(leave_request).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, uuid=None):
        leave_request = self.get_object()
        if leave_request.employee_id != request.user.id and request.user.role != 'HR_ADMIN':
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            LeaveService.cancel_leave(leave_request, cancelled_by=request.user)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(leave_request).data)


class ApprovalDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ApprovalDocumentSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_queryset(self):
        user = self.request.user
        queryset = ApprovalDocument.objects.select_related('company', 'leave_request', 'created_by')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)
