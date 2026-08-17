from django.db import models

from core.models.base import CompanyScopedModel


class WorkDriveFolder(CompanyScopedModel):
    folder_name = models.CharField(max_length=255)
    zoho_folder_id = models.CharField(max_length=150, unique=True)
    employee = models.OneToOneField(
        'core.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workdrive_folder',
    )

    class Meta:
        db_table = 'workdrive_folders'

    def __str__(self):
        return f"{self.folder_name} ({self.zoho_folder_id})"


class EmployeeDocument(CompanyScopedModel):
    employee = models.ForeignKey(
        'core.Employee',
        on_delete=models.CASCADE,
        related_name='documents',
    )
    folder = models.ForeignKey(
        WorkDriveFolder,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    document_name = models.CharField(max_length=255)
    document_type = models.CharField(max_length=100)
    zoho_file_id = models.CharField(max_length=150, unique=True)
    version = models.IntegerField(default=1)
    uploaded_by = models.ForeignKey(
        'core.Employee',
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents',
    )

    class Meta:
        db_table = 'employee_documents'

    def __str__(self):
        return f"{self.document_name} v{self.version} - {self.employee.get_full_name() or self.employee.username}"


class EmailLog(CompanyScopedModel):
    recipient = models.CharField(max_length=255)
    subject = models.TextField()
    template_name = models.CharField(max_length=150)
    status = models.CharField(max_length=30)
    message_id = models.CharField(max_length=150, null=True, blank=True)
    sent_by = models.ForeignKey(
        'core.Employee',
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_emails',
    )

    class Meta:
        db_table = 'email_logs'

    def __str__(self):
        return f"To: {self.recipient} | Subject: {self.subject[:30]}... | Status: {self.status}"
