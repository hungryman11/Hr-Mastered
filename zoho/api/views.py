from rest_framework import viewsets

from core.permissions import IsCompanyMember, IsHRAdmin
from zoho.models import EmailLog, EmployeeDocument, WorkDriveFolder
from zoho.serializers import EmailLogSerializer, EmployeeDocumentSerializer, WorkDriveFolderSerializer


class WorkDriveFolderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WorkDriveFolderSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_queryset(self):
        user = self.request.user
        queryset = WorkDriveFolder.objects.select_related('company', 'employee')
        if user.is_superuser:
            return queryset
        if user.role == 'HR_ADMIN':
            return queryset.filter(company=user.company)
        return queryset.filter(company=user.company, employee=user)


class EmployeeDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmployeeDocumentSerializer
    lookup_field = 'uuid'
    permission_classes = [IsCompanyMember]

    def get_queryset(self):
        user = self.request.user
        queryset = EmployeeDocument.objects.select_related('company', 'employee', 'folder', 'uploaded_by')
        if user.is_superuser:
            return queryset
        if user.role == 'HR_ADMIN':
            return queryset.filter(company=user.company)
        return queryset.filter(company=user.company, employee=user)


class EmailLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmailLogSerializer
    lookup_field = 'uuid'
    permission_classes = [IsHRAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = EmailLog.objects.select_related('company', 'sent_by')
        if user.is_superuser:
            return queryset
        return queryset.filter(company=user.company)
