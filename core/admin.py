from django.contrib import admin

from core.models import ApprovalDocument, Company, Department, Employee, LeaveBalance, LeaveRequest, LeaveType, OrgUnit


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'uuid', 'created_at')
    search_fields = ('name', 'uuid')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'uuid', 'created_at')
    list_filter = ('company',)
    search_fields = ('name', 'company__name', 'uuid')


@admin.register(OrgUnit)
class OrgUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit_type', 'company', 'parent', 'head', 'sort_order')
    list_filter = ('company', 'unit_type')
    search_fields = ('name', 'company__name')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'company', 'department', 'org_unit', 'role', 'is_staff')
    list_filter = ('company', 'department', 'org_unit', 'role', 'is_staff', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'uuid')
    autocomplete_fields = ('company', 'department', 'org_unit', 'manager', 'created_by', 'updated_by')


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'default_days')
    list_filter = ('company',)
    search_fields = ('name',)


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'allocated_days', 'used_days', 'company')
    list_filter = ('company', 'leave_type')
    search_fields = ('employee__username', 'employee__first_name', 'employee__last_name')


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status', 'company')
    list_filter = ('company', 'status', 'leave_type')
    search_fields = ('employee__username', 'employee__first_name', 'employee__last_name', 'reason')


@admin.register(ApprovalDocument)
class ApprovalDocumentAdmin(admin.ModelAdmin):
    list_display = ('leave_request', 'document_type', 'file_name', 'company', 'created_by', 'created_at')
    list_filter = ('company', 'document_type')
    search_fields = ('leave_request__employee__username', 'file_name')
