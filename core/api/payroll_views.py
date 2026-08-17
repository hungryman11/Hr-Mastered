from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from core.models import EmployeeRole, PayrollAdjustment, PayrollDeduction, PayrollProfile, PayrollRun, StatutoryRule
from core.payroll import PayrollService
from core.payroll_import import PayrollImportService
from core.payroll_serializers import PayrollAdjustmentSerializer, PayrollDeductionSerializer, PayrollProfileSerializer, PayrollRunSerializer, ReconcileSerializer, StatutoryRuleSerializer
from core.permissions import IsCompanyMember, IsFinanceOrHRAdmin


class CompanyPayrollViewSet(viewsets.ModelViewSet):
    permission_classes = [IsFinanceOrHRAdmin]
    lookup_field = 'uuid'
    def get_queryset(self):
        return self.queryset.filter(company=self.request.user.company) if not self.request.user.is_superuser else self.queryset.all()
    def perform_create(self, serializer): serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)
    def perform_update(self, serializer): serializer.save(updated_by=self.request.user)

class PayrollProfileViewSet(CompanyPayrollViewSet):
    queryset, serializer_class = PayrollProfile.objects.select_related('employee'), PayrollProfileSerializer

    @action(detail=False, methods=['post'])
    def validate_csv(self, request):
        uploaded = request.FILES.get('file')
        if uploaded is None:
            return Response({'detail': 'A CSV upload is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            valid_rows, errors = PayrollImportService.validate_profile_csv(request.user.company, uploaded)
        except ValidationError as exc:
            payload = exc.message_dict if hasattr(exc, 'message_dict') else {'detail': str(exc)}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response({'valid_rows': len(valid_rows), 'errors': errors}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def import_csv(self, request):
        uploaded = request.FILES.get('file')
        if uploaded is None:
            return Response({'detail': 'A CSV upload is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            imported = PayrollImportService.import_profiles(request.user.company, uploaded)
        except ValidationError as exc:
            payload = exc.message_dict if hasattr(exc, 'message_dict') else {'detail': str(exc)}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response({'imported_profiles': imported}, status=status.HTTP_200_OK)

class StatutoryRuleViewSet(CompanyPayrollViewSet):
    queryset, serializer_class = StatutoryRule.objects.all(), StatutoryRuleSerializer
    def get_permissions(self): return [IsFinanceOrHRAdmin()]

class PayrollAdjustmentViewSet(CompanyPayrollViewSet):
    queryset, serializer_class = PayrollAdjustment.objects.select_related('employee'), PayrollAdjustmentSerializer
    @action(detail=True, methods=['post'])
    def approve(self, request, uuid=None):
        adjustment = self.get_object()
        if request.user.role != EmployeeRole.FINANCE: return Response({'detail': 'Finance approval required.'}, status=403)
        adjustment.status, adjustment.approved_by, adjustment.updated_by = PayrollAdjustment.Status.APPROVED, request.user, request.user; adjustment.save()
        return Response(self.get_serializer(adjustment).data)

class PayrollRunViewSet(CompanyPayrollViewSet):
    queryset, serializer_class = PayrollRun.objects.all(), PayrollRunSerializer
    @action(detail=True, methods=['post'])
    def calculate(self, request, uuid=None): return self._service(request, lambda run: PayrollService.calculate(run, request.user))
    @action(detail=True, methods=['post'])
    def review(self, request, uuid=None): return self._service(request, lambda run: PayrollService.review_or_approve(run, request.user))
    @action(detail=True, methods=['post'])
    def approve(self, request, uuid=None): return self._service(request, lambda run: PayrollService.review_or_approve(run, request.user, True))
    @action(detail=True, methods=['post'])
    def export(self, request, uuid=None): return self._service(request, lambda run: PayrollService.export(run, request.user, request.data.get('format', 'PACK')), export=True)
    @action(detail=True, methods=['post'])
    def reconcile(self, request, uuid=None):
        data = ReconcileSerializer(data=request.data); data.is_valid(raise_exception=True)
        return self._service(request, lambda run: PayrollService.reconcile(run, request.user, **data.validated_data))
    def _service(self, request, callback, export=False):
        try:
            result = callback(self.get_object())
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'file_paths': [str(path) for path in result]} if export else self.get_serializer(result).data)


class PayrollDeductionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PayrollDeduction.objects.select_related('payroll_item__employee', 'payroll_item__payroll_run')
    serializer_class = PayrollDeductionSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset.filter(company=user.company) if not user.is_superuser else self.queryset
        return queryset if user.role in {EmployeeRole.HR_ADMIN, EmployeeRole.FINANCE} or user.is_superuser else queryset.filter(payroll_item__employee=user)

    @action(detail=True, methods=['post'])
    def contest(self, request, uuid=None):
        try:
            deduction = PayrollService.contest_deduction(self.get_object(), request.user, request.data.get('reason', ''))
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'uuid': str(deduction.uuid), 'is_held': deduction.is_held})

    @action(detail=True, methods=['post'])
    def resolve(self, request, uuid=None):
        try:
            deduction = PayrollService.resolve_deduction(self.get_object(), request.user, request.data.get('uphold', True), request.data.get('notes', ''))
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'uuid': str(deduction.uuid), 'amount': str(deduction.amount), 'is_held': deduction.is_held})
