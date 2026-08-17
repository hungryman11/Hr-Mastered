from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from django.core.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import ApprovalDecision, ApprovalDocument, Company, CompanyHoliday, CompanyWorkCalendar, DeliveryJob, Department, Employee, LeaveApprovalStep, LeaveBalance, LeaveRequest, LeaveType, OrgUnit, Position
from core.onboarding import ApprovalRoutingService, LeaveService, OnboardingService
from core.permissions import CanViewApprovalDecision, IsCompanyMember, IsHRAdmin, IsOrgAdmin, IsSuperUserOnly
from core.serializers import CompanySerializer, DepartmentSerializer, EmployeeSerializer, OrgUnitSerializer, PositionSerializer
from core.leave_serializers import AmendmentReasonSerializer, ApprovalDecisionSerializer, ApprovalDocumentSerializer, CompanyHolidaySerializer, CompanyWorkCalendarSerializer, DeliveryJobSerializer, LeaveAmendmentSerializer, LeaveApprovalStepSerializer, LeaveBalanceSerializer, LeaveRequestSerializer, LeaveTypeSerializer


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

    def get_permissions(self):
        return [IsHRAdmin()] if self.request.method not in ('GET', 'HEAD', 'OPTIONS') else [IsCompanyMember()]

    def get_queryset(self):
        user = self.request.user
        queryset = Department.objects.select_related('company')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class OrgUnitViewSet(viewsets.ModelViewSet):
    """
    Org units define the reporting hierarchy the leave-approval organogram is
    built from. Writes require IsOrgAdmin (a narrower grant than IsHRAdmin) so
    only deliberately-authorised people can restructure it.
    """
    serializer_class = OrgUnitSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_permissions(self):
        return [IsOrgAdmin()] if self.request.method not in ('GET', 'HEAD', 'OPTIONS') else [IsCompanyMember()]

    def get_queryset(self):
        user = self.request.user
        queryset = OrgUnit.objects.select_related('company', 'parent', 'head')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PositionViewSet(viewsets.ModelViewSet):
    serializer_class = PositionSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_permissions(self):
        return [IsHRAdmin()] if self.request.method not in ('GET', 'HEAD', 'OPTIONS') else [IsCompanyMember()]

    def get_queryset(self):
        user = self.request.user
        queryset = Position.objects.select_related('company', 'org_unit')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_permissions(self):
        # get_permissions() being overridden here means the permission_classes kwarg
        # on individual @action decorators (set_org_admin, onboard) is otherwise
        # silently ignored - DRF only consults it if get_permissions() itself checks
        # self.action. That previously let any HR Admin call set_org_admin and grant
        # is_org_admin to anyone, defeating the point of making it superuser-only.
        if self.action == 'set_org_admin':
            return [IsSuperUserOnly()]
        if self.action == 'onboard':
            return [IsHRAdmin()]
        if self.action == 'effective_kpis':
            return [IsCompanyMember()]
        return [IsHRAdmin()] if self.request.method not in ('GET', 'HEAD', 'OPTIONS') else [IsCompanyMember()]

    def get_queryset(self):
        user = self.request.user
        queryset = Employee.objects.select_related('company', 'department', 'org_unit', 'manager')
        if user.is_superuser:
            return queryset
        if user.role == 'HR_ADMIN':
            return queryset.filter(company=user.company)
        return queryset.filter(Q(company=user.company) & (Q(pk=user.pk) | Q(manager=user)))

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=['get'])
    def me(self, request):
        return Response(EmployeeSerializer(request.user, context={'request': request}).data)

    @action(detail=True, methods=['get'])
    def effective_kpis(self, request, uuid=None):
        """
        Preview effective resolved KPIs for an employee, detailing the inheritance chain
        (Global -> Department -> Position -> Employee Overrides), weights, and validation.
        """
        employee = self.get_object()
        user = request.user
        is_hr = user.is_superuser or getattr(user, 'role', None) == 'HR_ADMIN'
        is_manager_of_emp = (getattr(user, 'role', None) == 'MANAGER' and employee.manager_id == user.id)
        is_self = (employee.id == user.id)

        if not (is_hr or is_manager_of_emp or is_self):
            return Response(
                {'detail': "You do not have permission to view this employee's effective KPIs."},
                status=status.HTTP_403_FORBIDDEN,
            )

        as_of_date_str = request.query_params.get('as_of_date')
        as_of_date = None
        if as_of_date_str:
            try:
                from datetime import date
                as_of_date = date.fromisoformat(as_of_date_str)
            except ValueError:
                return Response(
                    {'as_of_date': 'Invalid date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        from core.kpi_service import KpiAssignmentService
        preview = KpiAssignmentService.get_effective_kpis_preview(employee, as_of_date=as_of_date)
        return Response(preview, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsSuperUserOnly])
    def set_org_admin(self, request, uuid=None):
        """
        Grant or revoke organogram-admin access for a specific employee.
        Deliberately superuser-only (not delegable to HR Admins, and not even
        to existing org admins) so this specific capability can't be handed
        out or escalated except by whoever controls the Django admin/superuser
        account. Body: {"is_org_admin": true|false}.
        """
        employee = self.get_object()
        if 'is_org_admin' not in request.data:
            return Response({'is_org_admin': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)
        value = request.data.get('is_org_admin')
        if not isinstance(value, bool):
            return Response({'is_org_admin': 'Must be a boolean.'}, status=status.HTTP_400_BAD_REQUEST)
        employee.is_org_admin = value
        employee.updated_by = request.user
        employee.save(update_fields=['is_org_admin', 'updated_by', 'updated_at'])
        return Response(EmployeeSerializer(employee, context={'request': request}).data)

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

    def get_permissions(self):
        return [IsHRAdmin()] if self.request.method not in ('GET', 'HEAD', 'OPTIONS') else [IsCompanyMember()]

    def get_queryset(self):
        user = self.request.user
        queryset = LeaveType.objects.select_related('company')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveBalanceSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_permissions(self):
        return [IsHRAdmin()] if self.request.method not in ('GET', 'HEAD', 'OPTIONS') else [IsCompanyMember()]

    def get_queryset(self):
        user = self.request.user
        queryset = LeaveBalance.objects.select_related('company', 'employee', 'leave_type')
        if user.is_superuser:
            return queryset
        if user.role == 'HR_ADMIN':
            return queryset.filter(company=user.company)
        return queryset.filter(company=user.company, employee=user)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CompanyHolidayViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyHolidaySerializer
    lookup_field = 'uuid'
    permission_classes = [IsHRAdmin]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return CompanyHoliday.objects.all()
        return CompanyHoliday.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CompanyWorkCalendarViewSet(viewsets.ModelViewSet):
    """HR-only configuration of the company work week and national-holiday policy."""

    serializer_class = CompanyWorkCalendarSerializer
    lookup_field = 'uuid'
    permission_classes = [IsHRAdmin]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return CompanyWorkCalendar.objects.all()
        return CompanyWorkCalendar.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


from rest_framework.parsers import FormParser, JSONParser, MultiPartParser


class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        queryset = LeaveRequest.objects.select_related('company', 'employee', 'leave_type', 'reviewed_by')
        if user.is_superuser:
            return queryset
        if user.role == 'HR_ADMIN':
            return queryset.filter(company=user.company)
        return queryset.filter(company=user.company).filter(
            Q(employee=user) | Q(approval_steps__approver=user)
        ).distinct()

    def get_object(self):
        # Keep detail routes subject to the same employee/approver scope as list routes.
        return super().get_object()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        document_file = data.get('document')

        try:
            leave_request = LeaveService.request_leave(
                employee=request.user,
                leave_type=data['leave_type'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                days_requested=None,
                reason=data.get('reason', ''),
                contact_during_leave=data['contact_during_leave'],
                emergency_contact_name=data['emergency_contact_name'],
                emergency_contact_phone=data['emergency_contact_phone'],
                handover_contact=data['handover_contact'],
                handover_notes=data['handover_notes'],
                document_file=document_file,
            )
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)
        return Response(LeaveRequestSerializer(leave_request, context={'request': request}).data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['get'])
    def routing(self, request, uuid=None):
        """Return the stored approval-step snapshot and the current pending stage."""
        leave_request = self.get_object()
        all_steps = leave_request.approval_steps.select_related('approver').order_by('sequence', 'id')
        current_steps = ApprovalRoutingService.get_current_steps(leave_request).select_related('approver')
        current_stage = current_steps.first().stage if current_steps.exists() else None
        return Response({
            'current_stage': current_stage,
            'current_approvers': EmployeeSerializer(
                [s.approver for s in current_steps], many=True, context={'request': request}
            ).data,
            'approval_steps': LeaveApprovalStepSerializer(all_steps, many=True).data,
        })

    @action(detail=False, methods=['get'], url_path='pending-approvals')
    def pending_approvals(self, request):
        """Return leave requests the authenticated user may approve now."""
        pending_steps = LeaveApprovalStep.objects.filter(
            company=request.user.company,
            approver=request.user,
            approval_round=F('leave_request__approval_round'),
            status=LeaveApprovalStep.Status.PENDING,
        ).select_related(
            'leave_request__employee__department',
            'leave_request__employee__org_unit',
            'leave_request__employee__position',
            'leave_request__leave_type',
        ).order_by('leave_request_id', 'sequence')

        queue, seen_request_ids = [], set()
        for step in pending_steps:
            leave_request = step.leave_request
            current_steps = ApprovalRoutingService.get_current_steps(leave_request)
            if not current_steps.filter(pk=step.pk).exists() or leave_request.pk in seen_request_ids:
                continue
            seen_request_ids.add(leave_request.pk)
            employee = leave_request.employee
            queue.append({
                'uuid': str(leave_request.uuid),
                'employee_uuid': str(employee.uuid),
                'employee_id': employee.id,
                'employee_name': employee.get_full_name() or employee.username,
                'department': employee.department.name if employee.department_id else None,
                'org_unit': employee.org_unit.name if employee.org_unit_id else None,
                'position': employee.position.title if employee.position_id else None,
                'leave_type': leave_request.leave_type.name,
                'start_date': leave_request.start_date,
                'end_date': leave_request.end_date,
                'working_days': leave_request.days_requested,
                'reason': leave_request.reason,
                'supporting_document_name': leave_request.supporting_document_name or leave_request.document_name,
                'supporting_document_url': leave_request.supporting_workdrive_url or leave_request.workdrive_url,
                'status': leave_request.status,
                'current_approval_step': LeaveApprovalStepSerializer(step).data,
                'approval_timeline': LeaveApprovalStepSerializer(
                    leave_request.approval_steps.select_related('approver').order_by('sequence', 'id'), many=True,
                ).data,
                'can_approve': True,
                'can_reject': True,
            })
        return Response(queue)

    @action(detail=True, methods=['post'])
    def approve(self, request, uuid=None):
        leave_request = self.get_object()
        # Ensure caller is assigned to the current approval stage
        current_steps = ApprovalRoutingService.get_current_steps(leave_request)
        if not current_steps.filter(approver=request.user).exists():
            return Response({'detail': 'You are not assigned to approve this leave request.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            LeaveService.approve_leave(leave_request, reviewed_by=request.user, reason=request.data.get('reason', ''))
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(self.get_serializer(leave_request).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, uuid=None):
        leave_request = self.get_object()
        reason = request.data.get('reason', '')
        # Ensure caller is assigned to the current approval stage
        current_steps = ApprovalRoutingService.get_current_steps(leave_request)
        if not current_steps.filter(approver=request.user).exists():
            return Response({'detail': 'You are not assigned to reject this leave request.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            LeaveService.reject_leave(leave_request, reviewed_by=request.user, reason=reason)
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(self.get_serializer(leave_request).data)

    @action(detail=True, methods=['post'], url_path='request-amendment')
    def request_amendment(self, request, uuid=None):
        leave_request = self.get_object()
        current_steps = ApprovalRoutingService.get_current_steps(leave_request)
        if not current_steps.filter(approver=request.user).exists():
            return Response({'detail': 'You are not assigned to amend this leave request.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = AmendmentReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            LeaveService.request_amendment(leave_request, request.user, serializer.validated_data['reason'])
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(leave_request).data)

    @action(detail=True, methods=['post'])
    def amend(self, request, uuid=None):
        leave_request = self.get_object()
        if leave_request.employee_id != request.user.id:
            return Response({'detail': 'Only the requester may amend this leave request.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = LeaveAmendmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            LeaveService.amend_leave(leave_request, request.user, **serializer.validated_data)
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(leave_request).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, uuid=None):
        leave_request = self.get_object()
        from core.models import EmployeeRole
        # Only the requester or HR admins (or superusers) may cancel a leave request
        if leave_request.employee_id != request.user.id and request.user.role != EmployeeRole.HR_ADMIN and not request.user.is_superuser:
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            LeaveService.cancel_leave(leave_request, cancelled_by=request.user)
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(self.get_serializer(leave_request).data)


class ApprovalDecisionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ApprovalDecisionSerializer
    lookup_field = 'uuid'
    permission_classes = [CanViewApprovalDecision]

    def get_queryset(self):
        user = self.request.user
        queryset = ApprovalDecision.objects.select_related('company', 'leave_request', 'approval_step', 'actor')
        if user.is_superuser:
            return queryset
        if user.role == 'HR_ADMIN':
            return queryset.filter(company=user.company)
        return queryset.filter(company=user.company).filter(
            Q(leave_request__employee=user) | Q(actor=user) | Q(leave_request__approval_steps__approver=user)
        ).distinct()


class ApprovalDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ApprovalDocumentSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_queryset(self):
        user = self.request.user
        queryset = ApprovalDocument.objects.select_related('company', 'leave_request', 'created_by')
        if user.is_superuser:
            return queryset
        if user.role == 'HR_ADMIN':
            return queryset.filter(company=user.company)
        return queryset.filter(company=user.company).filter(
            Q(leave_request__employee=user) | Q(leave_request__approval_steps__approver=user)
        ).distinct()


class DeliveryJobViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeliveryJobSerializer
    lookup_field = 'uuid'
    permission_classes = [IsHRAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = DeliveryJob.objects.select_related('company').order_by('-created_at')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)

    @action(detail=True, methods=['post'])
    def retry(self, request, uuid=None):
        job = self.get_object()
        if job.status == DeliveryJob.Status.SUCCEEDED:
            return Response({'detail': 'Successful deliveries cannot be retried.'}, status=status.HTTP_400_BAD_REQUEST)
        job.status = DeliveryJob.Status.PENDING
        job.attempts = 0
        job.last_error = ''
        job.completed_at = None
        job.available_at = timezone.now()
        job.locked_at = None
        job.updated_by = request.user
        job.save(update_fields=['status', 'attempts', 'last_error', 'completed_at', 'available_at', 'locked_at', 'updated_by', 'updated_at'])
        return Response(self.get_serializer(job).data)
