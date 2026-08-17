from rest_framework import serializers

from core.models import Company, Department, Employee, OrgUnit, Position
from core.models import LeaveApprovalPolicy, ApprovalDelegation
from core.models import (
    KpiCategory, KpiTemplate, KpiFramework, PerformanceCycle,
    EmployeeKpiAssignment, KpiMeasurement, KpiFrameworkItem,
    EmployeeKpiOverride, PerformanceReview, SalaryRecord,
)



class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ('uuid', 'name', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'created_at', 'updated_at')


class DepartmentSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Department
        fields = ('uuid', 'name', 'company', 'company_name', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'company', 'company_name', 'created_at', 'updated_at')

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user:
            return attrs
        company_id = getattr(request.user, 'company_id', None)
        instance = getattr(self, 'instance', None)
        if instance and instance.company_id != company_id and not request.user.is_superuser:
            raise serializers.ValidationError('Cannot modify a department outside your company.')
        if 'company' in attrs and attrs['company'].id != company_id and not request.user.is_superuser:
            raise serializers.ValidationError({'company': 'Must belong to your company.'})
        return attrs


class PositionSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    org_unit_name = serializers.CharField(source='org_unit.name', read_only=True)

    org_unit = serializers.PrimaryKeyRelatedField(queryset=OrgUnit.objects.none(), allow_null=True, required=False)

    class Meta:
        model = Position
        fields = ('id', 'uuid', 'company', 'company_name', 'title', 'code', 'org_unit', 'org_unit_name', 'description', 'active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'uuid', 'company', 'company_name', 'org_unit_name', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request or not getattr(request.user, 'company_id', None):
            return
        self.fields['org_unit'].queryset = OrgUnit.objects.filter(company=request.user.company)

    def validate(self, attrs):
        request = self.context.get('request')
        company_id = getattr(request.user, 'company_id', None)
        org_unit = attrs.get('org_unit')
        if org_unit and org_unit.company_id != company_id:
            raise serializers.ValidationError({'org_unit': 'Must belong to your company.'})
        return attrs


class KpiCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = KpiCategory
        fields = ('uuid', 'company', 'name', 'description', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'company', 'created_at', 'updated_at')


class KpiTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KpiTemplate
        fields = ('uuid', 'company', 'name', 'description', 'category', 'measurement_type', 'direction', 'default_target', 'default_weight', 'frequency', 'data_source', 'scoring_method', 'min_score', 'max_score', 'active', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'company', 'created_at', 'updated_at')


class KpiFrameworkSerializer(serializers.ModelSerializer):
    items = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    org_unit_name = serializers.CharField(source='org_unit.name', read_only=True)

    position = serializers.PrimaryKeyRelatedField(queryset=Position.objects.none(), allow_null=True, required=False)
    org_unit = serializers.PrimaryKeyRelatedField(queryset=OrgUnit.objects.none(), allow_null=True, required=False)

    class Meta:
        model = KpiFramework
        fields = ('uuid', 'company', 'name', 'scope_type', 'status', 'org_unit', 'org_unit_name', 'position', 'position_title', 'items', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'company', 'org_unit_name', 'position_title', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request or not getattr(request.user, 'company_id', None):
            return
        company = request.user.company
        self.fields['position'].queryset = Position.objects.filter(company=company)
        self.fields['org_unit'].queryset = OrgUnit.objects.filter(company=company)

    def validate(self, attrs):
        request = self.context.get('request')
        company_id = getattr(request.user, 'company_id', None)
        for field in ('position', 'org_unit'):
            value = attrs.get(field)
            if value and value.company_id != company_id:
                raise serializers.ValidationError({field: 'Must belong to your company.'})

        # Enforce scope/null constraint rules
        scope_type = attrs.get('scope_type') or (self.instance.scope_type if self.instance else None)
        position = attrs.get('position') if 'position' in attrs else (self.instance.position if self.instance else None)
        org_unit = attrs.get('org_unit') if 'org_unit' in attrs else (self.instance.org_unit if self.instance else None)

        if scope_type == KpiFramework.ScopeType.GLOBAL:
            if position is not None:
                raise serializers.ValidationError({'position': 'GLOBAL scope must not have a position. Set position to null.'})
            if org_unit is not None:
                raise serializers.ValidationError({'org_unit': 'GLOBAL scope must not have an org_unit. Set org_unit to null.'})
        elif scope_type == KpiFramework.ScopeType.DEPARTMENT:
            if org_unit is None:
                raise serializers.ValidationError({'org_unit': 'DEPARTMENT scope requires an org_unit.'})
            if position is not None:
                raise serializers.ValidationError({'position': 'DEPARTMENT scope must not have a position. Set position to null.'})
        elif scope_type == KpiFramework.ScopeType.POSITION:
            if position is None:
                raise serializers.ValidationError({'position': 'POSITION scope requires a position.'})

        return attrs


class PerformanceCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceCycle
        fields = ('uuid', 'company', 'name', 'start_date', 'end_date', 'review_deadline', 'locked', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'company', 'created_at', 'updated_at')


class EmployeeKpiAssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    score_evaluation = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EmployeeKpiAssignment
        fields = (
            'uuid', 'company', 'cycle', 'employee', 'employee_name', 'template',
            'template_name', 'measurement_type', 'direction', 'scoring_method',
            'category_name', 'target', 'weight', 'source',
            'score_evaluation', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'uuid', 'company', 'employee_name', 'template_name', 'measurement_type',
            'direction', 'scoring_method', 'category_name', 'score_evaluation',
            'created_at', 'updated_at',
        )

    def get_score_evaluation(self, obj):
        from core.kpi_scoring_service import KpiScoringService
        return KpiScoringService.evaluate_assignment(obj)



class KpiMeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = KpiMeasurement
        fields = ('uuid', 'company', 'assignment', 'measured_at', 'recorded_by', 'value', 'notes', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'company', 'measured_at', 'created_at', 'updated_at')


class PerformanceReviewSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_username = serializers.CharField(source='employee.username', read_only=True)
    department_name = serializers.CharField(source='employee.org_unit.name', read_only=True)
    position_title = serializers.CharField(source='employee.position.title', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)
    calibrated_by_name = serializers.CharField(source='calibrated_by.get_full_name', read_only=True)
    finalized_by_name = serializers.CharField(source='finalized_by.get_full_name', read_only=True)
    cycle_name = serializers.CharField(source='cycle.name', read_only=True)

    class Meta:
        model = PerformanceReview
        fields = (
            'uuid', 'company', 'cycle', 'cycle_name', 'employee', 'employee_name',
            'employee_username', 'department_name', 'position_title', 'reviewer',
            'reviewer_name', 'system_score', 'employee_self_score', 'employee_comments',
            'manager_score', 'manager_comments', 'hr_score', 'hr_comments',
            'calibrated_score', 'calibrated_by', 'calibrated_by_name', 'calibrated_at',
            'final_score', 'final_comments', 'status',
            'finalized_by', 'finalized_by_name', 'finalized_at',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'uuid', 'company', 'cycle_name', 'employee_name', 'employee_username',
            'department_name', 'position_title', 'reviewer_name', 'calibrated_by_name',
            'finalized_by_name', 'created_at', 'updated_at',
        )


class SalaryRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_username = serializers.CharField(source='employee.username', read_only=True)
    gross_salary = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    currency_display = serializers.CharField(source='get_currency_display', read_only=True)

    class Meta:
        model = SalaryRecord
        fields = (
            'uuid', 'company', 'employee', 'employee_name', 'employee_username',
            'effective_date', 'end_date', 'currency', 'currency_display',
            'base_salary', 'housing_allowance', 'transport_allowance',
            'meal_allowance', 'other_allowances', 'gross_salary',
            'reason', 'status', 'status_display',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'uuid', 'company', 'employee_name', 'employee_username',
            'gross_salary', 'status_display', 'currency_display',
            'created_at', 'updated_at',
        )


class OrgUnitSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    head_name = serializers.CharField(source='head.get_full_name', read_only=True)

    parent = serializers.PrimaryKeyRelatedField(queryset=OrgUnit.objects.none(), allow_null=True, required=False)
    head = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.none(), allow_null=True, required=False)

    class Meta:
        model = OrgUnit
        fields = ('uuid', 'company', 'company_name', 'name', 'unit_type', 'parent', 'parent_name', 'head', 'head_name', 'sort_order', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'company', 'company_name', 'parent_name', 'head_name', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request or not getattr(request.user, 'company_id', None):
            return
        company = request.user.company
        self.fields['parent'].queryset = OrgUnit.objects.filter(company=company)
        self.fields['head'].queryset = Employee.objects.filter(company=company)

    def validate(self, attrs):
        request = self.context.get('request')
        company_id = getattr(request.user, 'company_id', None)
        for field in ('parent', 'head'):
            value = attrs.get(field)
            if value and value.company_id != company_id:
                raise serializers.ValidationError({field: 'Must belong to your company.'})
        return attrs


class KpiFrameworkItemSerializer(serializers.ModelSerializer):
    template = serializers.PrimaryKeyRelatedField(queryset=KpiTemplate.objects.none())
    framework = serializers.PrimaryKeyRelatedField(queryset=KpiFramework.objects.none())

    class Meta:
        model = KpiFrameworkItem
        fields = ('id', 'framework', 'template', 'weight', 'target', 'scoring_method_override', 'direction_override', 'sequence', 'required')
        read_only_fields = ('id',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request or not getattr(request.user, 'company_id', None):
            return
        company = request.user.company
        self.fields['template'].queryset = KpiTemplate.objects.filter(company=company)
        self.fields['framework'].queryset = KpiFramework.objects.filter(company=company)

    def validate(self, attrs):
        framework = attrs.get('framework')
        template = attrs.get('template')
        if framework and template and framework.company_id != template.company_id:
            raise serializers.ValidationError('Framework and template must belong to the same company.')
        return attrs


class EmployeeKpiOverrideSerializer(serializers.ModelSerializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.none())
    template = serializers.PrimaryKeyRelatedField(queryset=KpiTemplate.objects.none())

    class Meta:
        model = EmployeeKpiOverride
        fields = ('id', 'company', 'employee', 'template', 'action_type', 'weight', 'target', 'active', 'effective_from', 'effective_to')
        read_only_fields = ('id', 'company')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request or not getattr(request.user, 'company_id', None):
            return
        company = request.user.company
        self.fields['employee'].queryset = Employee.objects.filter(company=company)
        self.fields['template'].queryset = KpiTemplate.objects.filter(company=company)

    def validate(self, attrs):
        employee = attrs.get('employee')
        template = attrs.get('template')
        if employee and template and employee.company_id != template.company_id:
            raise serializers.ValidationError('Employee and template must belong to the same company.')
        return attrs


class LeaveApprovalPolicySerializer(serializers.ModelSerializer):
    org_unit_name = serializers.CharField(source='org_unit.name', read_only=True)
    first_approver_name = serializers.CharField(source='first_approver_employee.get_full_name', read_only=True)
    final_approver_name = serializers.CharField(source='final_approver_employee.get_full_name', read_only=True)

    class Meta:
        model = LeaveApprovalPolicy
        fields = ('uuid', 'company', 'org_unit', 'org_unit_name', 'first_approver_type', 'first_approver_employee', 'first_approver_name', 'final_approver_type', 'final_approver_employee', 'final_approver_name', 'policy', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'company', 'org_unit_name', 'first_approver_name', 'final_approver_name', 'created_at', 'updated_at')


class ApprovalDelegationSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(source='approver.get_full_name', read_only=True)
    delegate_to_name = serializers.CharField(source='delegate_to.get_full_name', read_only=True)

    class Meta:
        model = ApprovalDelegation
        fields = ('uuid', 'company', 'approver', 'approver_name', 'delegate_to', 'delegate_to_name', 'start_date', 'end_date', 'active', 'reason', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'company', 'approver_name', 'delegate_to_name', 'created_at', 'updated_at')


class EmployeeSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    org_unit_name = serializers.CharField(source='org_unit.name', read_only=True)
    position_name = serializers.CharField(source='position.title', read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)

    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.none(), allow_null=True, required=False)
    org_unit = serializers.PrimaryKeyRelatedField(queryset=OrgUnit.objects.none(), allow_null=True, required=False)
    manager = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.none(), allow_null=True, required=False)
    position = serializers.PrimaryKeyRelatedField(queryset=Position.objects.none(), allow_null=True, required=False)

    class Meta:
        model = Employee
        fields = (
            'id',
            'uuid',
            'username',
            'first_name',
            'last_name',
            'email',
            'company',
            'company_name',
            'department',
            'department_name',
            'org_unit',
            'org_unit_name',
            'position',
            'position_name',
            'role',
            'manager',
            'manager_name',
            'is_org_admin',
            'is_active',
            'onboarding_status',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'uuid', 'company', 'company_name', 'department_name', 'org_unit_name', 'position_name', 'manager_name', 'is_org_admin', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request or not getattr(request.user, 'company_id', None):
            return
        company = request.user.company
        self.fields['department'].queryset = Department.objects.filter(company=company)
        self.fields['org_unit'].queryset = OrgUnit.objects.filter(company=company)
        self.fields['position'].queryset = Position.objects.filter(company=company)
        qs = Employee.objects.filter(company=company)
        instance = getattr(self, 'instance', None)
        # Only exclude self if instance is an actual Employee object (not a queryset in many=True case)
        if instance and hasattr(instance, 'pk'):
            qs = qs.exclude(pk=instance.pk)
        self.fields['manager'].queryset = qs

    def validate(self, attrs):
        request = self.context.get('request')
        instance = getattr(self, 'instance', None)
        company_id = getattr(request.user, 'company_id', None)
        for field in ('department', 'org_unit', 'manager', 'position'):
            value = attrs.get(field)
            if value and value.company_id != company_id:
                raise serializers.ValidationError({field: 'Must belong to your company.'})

        # Position / OrgUnit consistency validation:
        # If Employee.position exists AND Employee.position.org_unit exists,
        # Employee.org_unit must equal Employee.position.org_unit.
        pos = attrs.get('position') if 'position' in attrs else getattr(instance, 'position', None)
        ou = attrs.get('org_unit') if 'org_unit' in attrs else getattr(instance, 'org_unit', None)
        if pos and getattr(pos, 'org_unit_id', None):
            ou_id = getattr(ou, 'id', None)
            if not ou_id or ou_id != pos.org_unit_id:
                pos_unit_name = pos.org_unit.name if pos.org_unit else str(pos.org_unit_id)
                raise serializers.ValidationError({
                    'org_unit': f'Position "{pos.title}" belongs to org unit "{pos_unit_name}". Employee org unit must match.'
                })

        if instance is not None and request is not None:
            user = request.user
            is_org_admin = bool(user and (user.is_superuser or getattr(user, 'is_org_admin', False)))
            if not is_org_admin:
                restricted_changed = {}
                for field in ('role', 'manager', 'org_unit', 'position'):
                    if field in attrs and attrs[field] != getattr(instance, field):
                        restricted_changed[field] = 'Only an organization administrator can change this field.'
                if restricted_changed:
                    raise serializers.ValidationError(restricted_changed)
        return attrs

