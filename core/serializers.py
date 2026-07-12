from rest_framework import serializers

from core.models import Company, Department, Employee, OrgUnit


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
        read_only_fields = ('uuid', 'company_name', 'created_at', 'updated_at')


class OrgUnitSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    head_name = serializers.CharField(source='head.get_full_name', read_only=True)

    class Meta:
        model = OrgUnit
        fields = ('uuid', 'company', 'company_name', 'name', 'unit_type', 'parent', 'parent_name', 'head', 'head_name', 'sort_order', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'company_name', 'parent_name', 'head_name', 'created_at', 'updated_at')


class EmployeeSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    org_unit_name = serializers.CharField(source='org_unit.name', read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)

    class Meta:
        model = Employee
        fields = (
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
            'role',
            'manager',
            'manager_name',
            'onboarding_status',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('uuid', 'company_name', 'department_name', 'org_unit_name', 'manager_name', 'created_at', 'updated_at')
