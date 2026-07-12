from django.contrib import admin

from zoho.models import EmailLog, EmployeeDocument, WorkDriveFolder


@admin.register(WorkDriveFolder)
class WorkDriveFolderAdmin(admin.ModelAdmin):
    list_display = ('folder_name', 'company', 'zoho_folder_id', 'employee')
    list_filter = ('company',)
    search_fields = ('folder_name', 'zoho_folder_id', 'company__name')


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_name', 'company', 'employee', 'folder', 'version', 'zoho_file_id')
    list_filter = ('company', 'document_type', 'version')
    search_fields = ('document_name', 'zoho_file_id', 'employee__username')


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'subject', 'company', 'status', 'sent_by', 'created_at')
    list_filter = ('company', 'status')
    search_fields = ('recipient', 'subject', 'template_name')
