from django.core.management.base import BaseCommand
import os, tempfile
from core.models import Company, Employee
from zoho.services import ZohoWorkDriveService, ZohoMailService

class Command(BaseCommand):
    help = "Run a full Zoho integration demo: create company, employee, folder, upload a file, and send an email."

    def handle(self, *args, **options):
        # Ensure a company exists
        company, created = Company.objects.get_or_create(name='DemoCo')
        if created:
            self.stdout.write('Created company DemoCo')
        else:
            self.stdout.write('Using existing company DemoCo')
        # Ensure an employee exists
        employee, emp_created = Employee.objects.get_or_create(email='demo@example.com', defaults={'first_name': 'Demo', 'last_name': 'User', 'company': company})
        if emp_created:
            self.stdout.write('Created employee demo@example.com')
        else:
            self.stdout.write('Using existing employee demo@example.com')
        # Initialize Zoho service
        wd_service = ZohoWorkDriveService()
        # Create folder in Zoho WorkDrive
        folder_name = 'DemoFolder'
        zoho_folder = wd_service.create_folder(company=company, folder_name=folder_name, created_by=employee)
        self.stdout.write(f'Created Zoho WorkDrive folder: {folder_name} (ID: {zoho_folder.zoho_folder_id})')
        # Create a temporary file to upload
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
            tmp.write(b'Hello from Zoho demo file')
            tmp_path = tmp.name
        with open(tmp_path, 'rb') as f:
            file_content = f.read()
        doc = wd_service.upload_document(
            employee=employee,
            folder=zoho_folder,
            document_name='demo.txt',
            document_type='TXT',
            file_content=file_content,
            uploaded_by=employee,
        )
        self.stdout.write(f'Uploaded document to Zoho: {doc.document_name} (Zoho file ID: {doc.zoho_file_id})')
        # Send a test email via ZohoMailService
        mail_service = ZohoMailService()
        email_log = mail_service.send_and_log_email(
            company=company,
            recipient='demo@example.com',
            subject='Zoho Demo Email',
            body='This is a test email sent from the Zoho integration demo.',
            template_name='demo_email',
            sent_by=employee,
        )
        self.stdout.write(f'Email sent status: {email_log.status}')
        # Cleanup temporary file
        os.remove(tmp_path)
