from rest_framework import serializers

from core.models import LeaveBalance, LeaveRequest, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ('uuid', 'company', 'name', 'default_days', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'created_at', 'updated_at')


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    remaining_days = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ('uuid', 'company', 'employee', 'leave_type', 'leave_type_name', 'allocated_days', 'used_days', 'remaining_days', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'leave_type_name', 'remaining_days', 'created_at', 'updated_at')


class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

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
            'status',
            'reviewed_by',
            'reviewed_at',
            'rejection_reason',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('uuid', 'employee_name', 'leave_type_name', 'status', 'reviewed_by', 'reviewed_at', 'created_at', 'updated_at')

    def validate(self, attrs):
        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        days_requested = attrs.get('days_requested', getattr(self.instance, 'days_requested', None))

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({'end_date': 'End date must be on or after start date.'})

        if days_requested is not None and days_requested <= 0:
            raise serializers.ValidationError({'days_requested': 'Days requested must be greater than zero.'})

        return attrs
