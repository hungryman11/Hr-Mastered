from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.loan import LoanComplianceService
from core.loan_serializers import LoanCaseChecklistItemSerializer, LoanCaseSerializer, LoanProductSerializer
from core.models import EmployeeRole, LoanCase, LoanCaseChecklistItem, LoanProduct
from core.permissions import IsCompanyMember, IsHRAdmin


class CompanyLoanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsCompanyMember]
    lookup_field = 'uuid'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset.all()
        return self.queryset.filter(company=user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class LoanProductViewSet(CompanyLoanViewSet):
    queryset = LoanProduct.objects.all()
    serializer_class = LoanProductSerializer


class LoanCaseViewSet(CompanyLoanViewSet):
    queryset = LoanCase.objects.select_related('company', 'applicant', 'loan_product', 'assigned_checker')
    serializer_class = LoanCaseSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            case = LoanComplianceService.create_case(
                company=request.user.company,
                applicant=data['applicant'],
                product=data['loan_product'],
                amount=data['requested_amount'],
                purpose=data['purpose'],
                repayment_months=data['repayment_months'],
                collateral_type=data['collateral_type'],
                collateral_value=data['collateral_value'],
                collateral_details=data['collateral_details'],
                actor=request.user,
            )
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LoanCaseSerializer(case).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def verify_checklist(self, request, uuid=None):
        item_uuid = request.data.get('item_uuid')
        if not item_uuid:
            return Response({'detail': 'item_uuid is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            item = LoanCaseChecklistItem.objects.get(uuid=item_uuid, loan_case=self.get_object())
        except LoanCaseChecklistItem.DoesNotExist:
            return Response({'detail': 'Checklist item not found for this case.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            updated = LoanComplianceService.check_item(
                item=item,
                checker=request.user,
                status=request.data.get('status', item.status),
                note=request.data.get('note', ''),
                evidence_reference=request.data.get('evidence_reference', ''),
            )
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LoanCaseChecklistItemSerializer(updated).data)

    @action(detail=True, methods=['post'])
    def decide(self, request, uuid=None):
        try:
            updated = LoanComplianceService.decide(
                self.get_object(),
                request.user,
                request.data.get('decision', LoanCase.Status.APPROVED),
                request.data.get('reason', ''),
            )
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LoanCaseSerializer(updated).data)
