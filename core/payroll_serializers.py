from rest_framework import serializers
from core.models import Employee, PayrollAdjustment, PayrollDeduction, PayrollProfile, PayrollRun, ReconciliationRecord, StatutoryRule


class PayrollProfileSerializer(serializers.ModelSerializer):
    # Every other API in this app addresses employees by uuid (lookup_field='uuid' on
    # EmployeeViewSet, employee_uuid on PayrollDeductionSerializer, etc). The default
    # ModelSerializer field here would instead expect the numeric pk, which is not what
    # any client actually has - it made profile creation reject every valid uuid.
    employee = serializers.SlugRelatedField(slug_field='uuid', queryset=Employee.objects.all())

    class Meta:
        model = PayrollProfile
        fields = ('uuid', 'employee', 'employee_number', 'base_salary', 'bank_account_ciphertext', 'bank_code', 'pension_id_ciphertext', 'tax_id_ciphertext', 'employment_status', 'hire_date', 'termination_date', 'data_processing_consented_at')
        extra_kwargs = {
            'bank_account_ciphertext': {'write_only': True},
            'pension_id_ciphertext': {'write_only': True},
            'tax_id_ciphertext': {'write_only': True},
        }

    def validate_base_salary(self, value):
        if value < 0: raise serializers.ValidationError('Salary cannot be negative.')
        return value

    def validate_bank_code(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError('Bank code must contain digits only.')
        return value

    def validate(self, attrs):
        employee = attrs.get('employee', getattr(self.instance, 'employee', None))
        request = self.context.get('request')
        if request and employee and not request.user.is_superuser and employee.company_id != request.user.company_id:
            raise serializers.ValidationError({'employee': 'Employee must belong to your company.'})
        return attrs


class StatutoryRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatutoryRule
        fields = ('uuid', 'kind', 'rate_percent', 'effective_from', 'effective_to', 'is_active')

    def validate_rate_percent(self, value):
        if value < 0 or value > 100: raise serializers.ValidationError('Rate must be between 0 and 100.')
        return value


class PayrollAdjustmentSerializer(serializers.ModelSerializer):
    # Same uuid-vs-pk issue as PayrollProfileSerializer.employee above.
    employee = serializers.SlugRelatedField(slug_field='uuid', queryset=Employee.objects.all())

    class Meta:
        model = PayrollAdjustment
        fields = ('uuid', 'employee', 'kind', 'name', 'amount', 'month', 'reason', 'evidence_reference', 'status', 'approved_by')
        read_only_fields = ('approved_by',)

    def validate(self, attrs):
        if attrs.get('amount', 0) <= 0: raise serializers.ValidationError({'amount': 'Amount must be positive.'})
        if len(attrs.get('reason', '').strip()) < 10: raise serializers.ValidationError({'reason': 'Provide a documented reason of at least 10 characters.'})
        return attrs


class ReconciliationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReconciliationRecord
        fields = ('uuid', 'bank_reference', 'result', 'details', 'reconciled_by', 'created_at')
        read_only_fields = fields


class PayrollRunSerializer(serializers.ModelSerializer):
    reconciliation = ReconciliationRecordSerializer(read_only=True)

    class Meta:
        model = PayrollRun
        fields = ('uuid', 'month', 'status', 'total_gross', 'total_deductions', 'total_held', 'net_payroll', 'calculated_by', 'approved_by', 'approved_at', 'created_at', 'reconciliation')
        read_only_fields = fields[2:]


class PayrollDeductionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='payroll_item.employee.get_full_name', read_only=True)
    employee_uuid = serializers.UUIDField(source='payroll_item.employee.uuid', read_only=True)
    payroll_run_uuid = serializers.UUIDField(source='payroll_item.payroll_run.uuid', read_only=True)
    payroll_month = serializers.DateField(source='payroll_item.payroll_run.month', read_only=True)

    class Meta:
        model = PayrollDeduction
        fields = (
            'uuid', 'kind', 'name', 'amount', 'reason', 'is_held', 'contested_at',
            'contest_reason', 'resolution_notes', 'employee_name', 'employee_uuid',
            'payroll_run_uuid', 'payroll_month',
        )
        read_only_fields = fields


class ReconcileSerializer(serializers.Serializer):
    bank_reference = serializers.CharField(min_length=1, max_length=100)
    result = serializers.ChoiceField(choices=['SUCCESS', 'FAILED'])
    details = serializers.JSONField(required=False, default=dict)
