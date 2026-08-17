from django.core.exceptions import ValidationError
from rest_framework import serializers

from core.models import ApprovalDocument, CompanyHoliday, CompanyWorkCalendar, DeliveryJob, LeaveApprovalStep, LeaveBalance, LeaveRequest, LeaveType, ApprovalDecision, Employee


class LeaveApprovalStepSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(source='approver.get_full_name', read_only=True)

    class Meta:
        model = LeaveApprovalStep
        fields = ('uuid', 'sequence', 'stage', 'approver', 'approver_name', 'status', 'decision_reason', 'decided_at')
        read_only_fields = fields


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = (
            'uuid', 'company', 'name', 'default_days', 'requires_supporting_document',
            'max_days_per_request', 'carry_over_days', 'proration_rule',
            'created_at', 'updated_at',
        )
        read_only_fields = ('uuid', 'company', 'created_at', 'updated_at')

    def validate(self, attrs):
        # Ensure default_days is sensible and prevent cross-company assignment
        request = self.context.get('request')
        if not request or not request.user:
            return attrs
        company_id = getattr(request.user, 'company_id', None)
        instance = getattr(self, 'instance', None)
        # If updating an existing LeaveType, ensure it belongs to the same company
        if instance and instance.company_id != company_id and not request.user.is_superuser:
            raise serializers.ValidationError('Cannot modify a leave type outside your company.')
        # Defensive: if payload contains company (should be read-only), reject mismatches
        if 'company' in attrs and attrs['company'].id != company_id and not request.user.is_superuser:
            raise serializers.ValidationError({'company': 'Must belong to your company.'})
        default_days = attrs.get('default_days')
        if default_days is not None and default_days < 0:
            raise serializers.ValidationError({'default_days': 'Must be zero or positive.'})
        return attrs


class CompanyHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyHoliday
        fields = ('uuid', 'company', 'name', 'date', 'is_national', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'company', 'created_at', 'updated_at')

    def validate_date(self, value):
        if value.year < 2020 or value.year > 2100:
            raise serializers.ValidationError('Holiday date must be between 2020 and 2100.')
        return value


class CompanyWorkCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyWorkCalendar
        fields = ('uuid', 'company', 'working_weekdays', 'include_nigerian_public_holidays', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'company', 'created_at', 'updated_at')

    def validate_working_weekdays(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError('Select at least one working weekday.')
        if any(not isinstance(day, int) or isinstance(day, bool) or day < 0 or day > 6 for day in value):
            raise serializers.ValidationError('Weekdays must be integers from 0 (Monday) to 6 (Sunday).')
        if len(set(value)) != len(value):
            raise serializers.ValidationError('Weekdays must not contain duplicates.')
        return value


class AmendmentReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=1, max_length=5000, trim_whitespace=True)


class LeaveAmendmentSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(min_length=1, max_length=5000, trim_whitespace=True)
    contact_during_leave = serializers.CharField(min_length=1, max_length=255, trim_whitespace=True)
    emergency_contact_name = serializers.CharField(min_length=1, max_length=255, trim_whitespace=True)
    emergency_contact_phone = serializers.CharField(min_length=1, max_length=50, trim_whitespace=True)
    handover_contact = serializers.CharField(min_length=1, max_length=255, trim_whitespace=True)
    handover_notes = serializers.CharField(min_length=1, max_length=5000, trim_whitespace=True)
    document = serializers.FileField(required=False, write_only=True)

    def validate(self, attrs):
        if attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError({'end_date': 'End date must be on or after start date.'})
        return attrs


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    remaining_days = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.none())
    leave_type = serializers.PrimaryKeyRelatedField(queryset=LeaveType.objects.none())

    class Meta:
        model = LeaveBalance
        fields = (
            'uuid', 'company', 'employee', 'leave_type', 'leave_type_name',
            'year', 'allocated_days', 'carried_over_days', 'used_days', 'remaining_days',
            'created_at', 'updated_at',
        )
        read_only_fields = ('uuid', 'company', 'leave_type_name', 'remaining_days', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request or not getattr(request.user, 'company_id', None):
            return
        company = request.user.company
        self.fields['employee'].queryset = Employee.objects.filter(company=company)
        self.fields['leave_type'].queryset = LeaveType.objects.filter(company=company)

    def validate(self, attrs):
        company_id = self.context['request'].user.company_id
        for field in ('employee', 'leave_type'):
            value = attrs.get(field)
            if value and value.company_id != company_id:
                raise serializers.ValidationError({field: 'Must belong to your company.'})
        return attrs


class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    document = serializers.FileField(write_only=True, required=False)
    approval_steps = LeaveApprovalStepSerializer(many=True, read_only=True)
    approval_decisions = serializers.SerializerMethodField()

    def get_approval_decisions(self, obj):
        decisions = obj.approval_decisions.select_related('actor').order_by('decided_at')
        return ApprovalDecisionSerializer(decisions, many=True).data

    leave_type = serializers.PrimaryKeyRelatedField(queryset=LeaveType.objects.none())
    days_requested = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = (
            'uuid',
            'company',
            'employee',
            'employee_name',
            'leave_type',
            'leave_type_name',
            'start_date',
            'end_date',
            'days_requested',
            'reason',
            'contact_during_leave',
            'emergency_contact_name',
            'emergency_contact_phone',
            'handover_contact',
            'handover_notes',
            'document',
            'document_name',
            'zoho_file_id',
            'workdrive_url',
            'supporting_document_name',
            'supporting_zoho_file_id',
            'supporting_workdrive_url',
            'status',
            'reviewed_by',
            'reviewed_at',
            'rejection_reason',
            'created_at',
            'updated_at',
            'approval_steps',
            'approval_decisions',
        )
        read_only_fields = (
            'approval_decisions',
            'uuid',
            'company',
            'employee',
            'employee_name',
            'leave_type_name',
            'document_name',
            'zoho_file_id',
            'workdrive_url',
            'supporting_document_name',
            'supporting_zoho_file_id',
            'supporting_workdrive_url',
            'status',
            'reviewed_by',
            'reviewed_at',
            'created_at',
            'updated_at',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request or not getattr(request.user, 'company_id', None):
            return
        company = request.user.company
        self.fields['leave_type'].queryset = LeaveType.objects.filter(company=company)

    def validate(self, attrs):
        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({'end_date': 'End date must be on or after start date.'})

        reason = attrs.get('reason', '')
        if not reason or not reason.strip():
            raise serializers.ValidationError({'reason': 'Reason for leave is required.'})

        # Validate supporting document only when one is explicitly supplied
        document = attrs.get('document')
        if document:
            from core.onboarding import LeaveService
            try:
                LeaveService.validate_document(document)
            except ValidationError as exc:
                raise serializers.ValidationError({'document': exc.messages}) from exc

        for field in ('contact_during_leave', 'emergency_contact_name', 'emergency_contact_phone', 'handover_contact', 'handover_notes'):
            if not attrs.get(field, getattr(self.instance, field, '')).strip():
                raise serializers.ValidationError({field: 'This field is required to generate the leave document.'})

        return attrs


class ApprovalDecisionSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True)

    class Meta:
        model = ApprovalDecision
        fields = ('uuid', 'company', 'leave_request', 'approval_step', 'actor', 'actor_name', 'stage', 'sequence', 'decision', 'reason', 'decided_at')
        read_only_fields = fields


class DeliveryJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryJob
        fields = ('uuid', 'kind', 'status', 'attempts', 'last_error', 'available_at', 'locked_at', 'completed_at', 'created_at', 'updated_at')
        read_only_fields = fields


class ApprovalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalDocument
        fields = ('uuid', 'company', 'leave_request', 'document_type', 'file_name', 'file_path', 'created_by', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'file_name', 'file_path', 'created_at', 'updated_at')
