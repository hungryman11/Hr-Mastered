from django.contrib import admin

from core.models import ApprovalDocument, Company, CompanyHoliday, CompanyWorkCalendar, Department, Employee, LeaveBalance, LeaveRequest, LeaveType, OrgUnit, LeaveApprovalPolicy, ApprovalDelegation


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
    list_display = ('username', 'email', 'company', 'department', 'org_unit', 'role', 'is_org_admin', 'is_staff')
    list_filter = ('company', 'department', 'org_unit', 'role', 'is_org_admin', 'is_staff', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'uuid')
    autocomplete_fields = ('company', 'department', 'org_unit', 'manager', 'created_by', 'updated_by')


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'default_days', 'requires_supporting_document')
    list_filter = ('company',)
    search_fields = ('name',)


@admin.register(CompanyHoliday)
class CompanyHolidayAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'company', 'is_national')
    list_filter = ('company', 'is_national')
    search_fields = ('name',)


@admin.register(CompanyWorkCalendar)
class CompanyWorkCalendarAdmin(admin.ModelAdmin):
    list_display = ('company', 'working_weekdays', 'include_nigerian_public_holidays')
    list_filter = ('include_nigerian_public_holidays',)
    search_fields = ('company__name',)


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


@admin.register(LeaveApprovalPolicy)
class LeaveApprovalPolicyAdmin(admin.ModelAdmin):
    list_display = ('org_unit', 'company', 'first_approver_type', 'final_approver_type')
    list_filter = ('company', 'first_approver_type', 'final_approver_type')
    search_fields = ('org_unit__name',)


@admin.register(ApprovalDelegation)
class ApprovalDelegationAdmin(admin.ModelAdmin):
    list_display = ('approver', 'delegate_to', 'start_date', 'end_date', 'active')
    list_filter = ('company', 'active')
    search_fields = ('approver__username', 'delegate_to__username')


from core.models import KpiCategory, KpiTemplate, KpiFramework, PerformanceCycle, EmployeeKpiAssignment, KpiMeasurement


@admin.register(KpiCategory)
class KpiCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'company')
    search_fields = ('name',)


@admin.register(KpiTemplate)
class KpiTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'measurement_type', 'direction', 'active')
    list_filter = ('company', 'measurement_type', 'direction', 'active')


@admin.register(KpiFramework)
class KpiFrameworkAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'scope_type')
    list_filter = ('company', 'scope_type')


@admin.register(PerformanceCycle)
class PerformanceCycleAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'start_date', 'end_date', 'locked')
    list_filter = ('company', 'locked')


@admin.register(EmployeeKpiAssignment)
class EmployeeKpiAssignmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'template', 'cycle', 'weight')
    list_filter = ('company', 'cycle')


@admin.register(KpiMeasurement)
class KpiMeasurementAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'measured_at', 'value')
    list_filter = ('company',)
