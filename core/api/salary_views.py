from django.db.models import Q
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import SalaryRecord, Employee, EmployeeRole
from core.serializers import SalaryRecordSerializer
from core.permissions import IsHRAdmin


class SalaryRecordViewSet(viewsets.ModelViewSet):
    """
    Salary record management with role-based access:

    - HR Admins can CREATE, READ, UPDATE, and manage all company salary records.
    - Employees can only READ their own salary records (no write access).
    - Cross-company isolation is enforced at the queryset level.
    """

    queryset = SalaryRecord.objects.select_related('employee').all()
    serializer_class = SalaryRecordSerializer
    lookup_field = 'uuid'
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not getattr(user, 'company_id', None):
            return qs.none()

        base_qs = qs.filter(company=user.company)

        # HR admins and superusers see all company records
        if user.is_superuser or getattr(user, 'role', None) == EmployeeRole.HR_ADMIN:
            employee_uuid = self.request.query_params.get('employee_uuid')
            if employee_uuid:
                base_qs = base_qs.filter(employee__uuid=employee_uuid)
            status_filter = self.request.query_params.get('status')
            if status_filter:
                base_qs = base_qs.filter(status=status_filter.upper())
            return base_qs

        # Self-service access exposes the current record only; HR retains the
        # company-scoped historical ledger.
        return base_qs.filter(employee=user, status=SalaryRecord.Status.ACTIVE)

    def _require_hr(self):
        """Returns True if the request user has HR write permission."""
        user = self.request.user
        return user.is_superuser or getattr(user, 'role', None) == EmployeeRole.HR_ADMIN

    def create(self, request, *args, **kwargs):
        if not self._require_hr():
            return Response(
                {'detail': 'Only HR Admins can create salary records.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not self._require_hr():
            return Response(
                {'detail': 'Only HR Admins can update salary records.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not self._require_hr():
            return Response(
                {'detail': 'Only HR Admins can delete salary records.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(
            company=self.request.user.company,
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=['post'], permission_classes=[IsHRAdmin])
    def supersede(self, request):
        """
        Supersede the current ACTIVE salary record for an employee and create a new one.

        Payload:
          {
            "employee_uuid": "...",
            "effective_date": "YYYY-MM-DD",
            "base_salary": ...,
            "housing_allowance": ...,
            "transport_allowance": ...,
            "meal_allowance": ...,
            "other_allowances": ...,
            "currency": "NGN",
            "reason": "..."
          }
        """
        user = request.user
        employee_uuid = request.data.get('employee_uuid')
        if not employee_uuid:
            return Response(
                {'employee_uuid': 'This field is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            employee = Employee.objects.get(uuid=employee_uuid, company=user.company)
        except Employee.DoesNotExist:
            return Response(
                {'detail': 'Employee not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        effective_date = request.data.get('effective_date')
        if not effective_date:
            return Response(
                {'effective_date': 'This field is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Supersede existing ACTIVE record(s) for this employee
        active_records = SalaryRecord.objects.filter(
            company=user.company,
            employee=employee,
            status=SalaryRecord.Status.ACTIVE,
        )
        from datetime import date as date_type
        from datetime import datetime
        if isinstance(effective_date, str):
            new_effective = datetime.strptime(effective_date, '%Y-%m-%d').date()
        else:
            new_effective = effective_date

        for record in active_records:
            # Close open-ended record the day before new effective date
            if record.end_date is None or record.end_date >= new_effective:
                import datetime as dt
                record.end_date = new_effective - dt.timedelta(days=1)
            record.status = SalaryRecord.Status.SUPERSEDED
            # Bypass full_clean overlap check since we're explicitly superseding
            super(SalaryRecord, record).save(update_fields=['end_date', 'status', 'updated_at'])

        # Build new salary record data
        new_data = {
            'employee': employee.pk,
            'effective_date': effective_date,
            'end_date': request.data.get('end_date', None),
            'currency': request.data.get('currency', SalaryRecord.Currency.NGN),
            'base_salary': request.data.get('base_salary', '0.00'),
            'housing_allowance': request.data.get('housing_allowance', '0.00'),
            'transport_allowance': request.data.get('transport_allowance', '0.00'),
            'meal_allowance': request.data.get('meal_allowance', '0.00'),
            'other_allowances': request.data.get('other_allowances', '0.00'),
            'reason': request.data.get('reason', ''),
            'status': SalaryRecord.Status.ACTIVE,
        }
        serializer = SalaryRecordSerializer(data=new_data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            instance = serializer.save(
                company=user.company,
                created_by=user,
                updated_by=user,
            )
        except DjangoValidationError as exc:
            payload = exc.message_dict if hasattr(exc, 'message_dict') else {'detail': str(exc)}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

        return Response(SalaryRecordSerializer(instance).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Return the current ACTIVE salary record(s) for the authenticated employee,
        or — for HR — for the employee specified via ?employee_uuid=.
        """
        user = request.user
        if not getattr(user, 'company_id', None):
            return Response({'detail': 'No company context.'}, status=status.HTTP_403_FORBIDDEN)

        is_hr = user.is_superuser or getattr(user, 'role', None) == EmployeeRole.HR_ADMIN
        employee_uuid = request.query_params.get('employee_uuid')

        if employee_uuid:
            if not is_hr:
                # Employees may only query their own
                if str(user.uuid) != employee_uuid:
                    return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            try:
                target = Employee.objects.get(uuid=employee_uuid, company=user.company)
            except Employee.DoesNotExist:
                return Response({'detail': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            target = user

        record = SalaryRecord.objects.filter(
            company=user.company,
            employee=target,
            status=SalaryRecord.Status.ACTIVE,
        ).first()

        if not record:
            return Response({'detail': 'No active salary record found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(SalaryRecordSerializer(record).data, status=status.HTTP_200_OK)
