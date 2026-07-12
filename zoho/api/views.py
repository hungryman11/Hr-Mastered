from rest_framework import viewsets

from zoho.models import EmailLog, EmployeeDocument, WorkDriveFolder
from zoho.serializers import EmailLogSerializer, EmployeeDocumentSerializer, WorkDriveFolderSerializer


class WorkDriveFolderViewSet(viewsets.ModelViewSet):
    serializer_class = WorkDriveFolderSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        user = self.request.user
        queryset = WorkDriveFolder.objects.select_related('company', 'employee')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)


class EmployeeDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeDocumentSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        user = self.request.user
        queryset = EmployeeDocument.objects.select_related('company', 'employee', 'folder', 'uploaded_by')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)


class EmailLogViewSet(viewsets.ModelViewSet):
    serializer_class = EmailLogSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        user = self.request.user
        queryset = EmailLog.objects.select_related('company', 'sent_by')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)
