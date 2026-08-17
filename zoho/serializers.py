from rest_framework import serializers

from zoho.models import EmailLog, EmployeeDocument, WorkDriveFolder


class WorkDriveFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkDriveFolder
        fields = ('uuid', 'company', 'folder_name', 'zoho_folder_id', 'employee', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'zoho_folder_id', 'created_at', 'updated_at')


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDocument
        fields = (
            'uuid',
            'company',
            'employee',
            'folder',
            'document_name',
            'document_type',
            'zoho_file_id',
            'version',
            'uploaded_by',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('uuid', 'zoho_file_id', 'version', 'created_at', 'updated_at')


class EmailLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailLog
        fields = ('uuid', 'company', 'recipient', 'subject', 'template_name', 'status', 'message_id', 'sent_by', 'created_at')
        read_only_fields = ('uuid', 'created_at')
