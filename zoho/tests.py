from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.db import IntegrityError
from core.models import Company, Employee
from zoho.models import WorkDriveFolder, EmployeeDocument, EmailLog
from zoho.services import get_zoho_access_token, get_zoho_auth_headers, get_zoho_config

class ZohoServiceTests(TestCase):
    @override_settings(
        ZOHO_CLIENT_ID="client-id",
        ZOHO_CLIENT_SECRET="client-secret",
        ZOHO_REFRESH_TOKEN="refresh-token",
        ZOHO_ORG_ID="12345",
    )
    def test_get_zoho_config_returns_values(self):
        config = get_zoho_config()
        self.assertEqual(config["client_id"], "client-id")
        self.assertEqual(config["client_secret"], "client-secret")
        self.assertEqual(config["refresh_token"], "refresh-token")
        self.assertEqual(config["org_id"], "12345")

    @override_settings(ZOHO_USE_MOCK=False, ZOHO_CLIENT_ID="", ZOHO_CLIENT_SECRET="client-secret", ZOHO_REFRESH_TOKEN="refresh-token")
    def test_get_zoho_config_raises_when_required_setting_missing(self):
        with self.assertRaises(ImproperlyConfigured):
            get_zoho_config()

    @override_settings(ZOHO_USE_MOCK=True, ZOHO_ORG_ID="67890")
    def test_mock_mode_returns_local_token_and_headers(self):
        token = get_zoho_access_token()
        headers = get_zoho_auth_headers()
        self.assertEqual(token, "mock-access-token")
        self.assertEqual(headers["Authorization"], "Bearer mock-access-token")
        self.assertEqual(headers["X-Org-Id"], "67890")


class ZohoIntegrationTests(TestCase):
    def test_home_page_renders_presentation_landing_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'HR Platform Demo')
        self.assertContains(response, 'Zoho Mock Mode')

    def setUp(self):
        self.company = Company.objects.create(name="Globex Corp")
        self.employee = Employee.objects.create_user(
            username="homersimpson",
            email="homer@globex.com",
            password="doh!",
            company=self.company
        )
        self.folder = WorkDriveFolder.objects.create(
            company=self.company,
            folder_name="Employees",
            zoho_folder_id="zoho_fld_111"
        )

    def test_workdrive_folder_creation(self):
        """Verify WorkDriveFolder properties and unique constraint."""
        self.assertEqual(self.folder.folder_name, "Employees")
        self.assertEqual(self.folder.zoho_folder_id, "zoho_fld_111")
        
        # Test unique constraint on zoho_folder_id
        with self.assertRaises(IntegrityError):
            WorkDriveFolder.objects.create(
                company=self.company,
                folder_name="Recruitment",
                zoho_folder_id="zoho_fld_111" # Duplicate
            )

    def test_employee_document_versioning(self):
        """Verify EmployeeDocument fields and default versioning."""
        doc = EmployeeDocument.objects.create(
            company=self.company,
            employee=self.employee,
            folder=self.folder,
            document_name="Passport.pdf",
            document_type="PDF",
            zoho_file_id="zoho_file_222",
            uploaded_by=self.employee
        )
        
        self.assertEqual(doc.version, 1) # Default value
        self.assertEqual(doc.document_name, "Passport.pdf")
        self.assertEqual(doc.zoho_file_id, "zoho_file_222")

        # Test unique constraint on zoho_file_id
        with self.assertRaises(IntegrityError):
            EmployeeDocument.objects.create(
                company=self.company,
                employee=self.employee,
                folder=self.folder,
                document_name="CV.pdf",
                document_type="PDF",
                zoho_file_id="zoho_file_222" # Duplicate
            )

    def test_email_log_creation(self):
        """Verify EmailLog creation and audit attributes."""
        log = EmailLog.objects.create(
            company=self.company,
            recipient="homer@globex.com",
            subject="Welcome to Globex!",
            template_name="welcome_email",
            status="SENT",
            message_id="zoho_msg_333",
            sent_by=self.employee
        )

        self.assertEqual(log.recipient, "homer@globex.com")
        self.assertEqual(log.status, "SENT")
        self.assertEqual(log.message_id, "zoho_msg_333")
