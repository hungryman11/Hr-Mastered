from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.db import IntegrityError
from unittest.mock import patch
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
    @override_settings(ZOHO_USE_MOCK=True)
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


@override_settings(ZOHO_USE_MOCK=True, DEBUG=True)
class ZohoAuthTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Default Company")
        self.employee = Employee.objects.create_user(
            username="zoho.user",
            email="zoho.user@example.com",
            password="password123",
            company=self.company,
        )

    def test_zoho_login_url_generation_happy_path(self):
        """In mock mode the login_url must skip the real Zoho screen entirely and
        point straight back at our own redirect_uri with a usable code+state, so the
        whole login flow can be built/tested with zero real Zoho credentials."""
        response = self.client.get('/api/zoho/auth/login-url/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("login_url", response.data)
        login_url = response.data["login_url"]
        self.assertNotIn("accounts.zoho.com", login_url)
        self.assertIn(response.data["redirect_uri"], login_url)
        self.assertIn("code=mock_auth_code", login_url)
        self.assertIn("state=", login_url)

    def test_mock_login_url_end_to_end_flow_happy_path(self):
        """Simulates exactly what a browser does: follow login_url's own code+state
        straight into the callback, with no knowledge of Zoho at all."""
        from urllib.parse import urlsplit, parse_qs

        login_response = self.client.get('/api/zoho/auth/login-url/')
        parsed = urlsplit(login_response.data["login_url"])
        query = parse_qs(parsed.query)
        code, state = query["code"][0], query["state"][0]

        callback_response = self.client.get(f'/api/zoho/auth/callback/?code={code}&state={state}')
        self.assertEqual(callback_response.status_code, 200)
        self.assertEqual(callback_response.data["employee"]["email"], "zoho.user@example.com")

    def test_zoho_demo_does_not_expose_access_token_boundary(self):
        response = self.client.get('/zoho-demo/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('headers', response.json())
        self.assertNotIn('Authorization', response.content.decode())

    def test_zoho_oauth_callback_happy_path(self):
        self.client.get('/api/zoho/auth/login-url/')
        state = self.client.session['zoho_oauth_state']
        response = self.client.get(f'/api/zoho/auth/callback/?code=mock_auth_code&state={state}')
        self.assertEqual(response.status_code, 200)
        self.assertIn("employee", response.data)
        self.assertEqual(response.data["employee"]["email"], "zoho.user@example.com")
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.zoho_user_id, 'zoho_usr_12345')

    def test_zoho_oauth_callback_missing_code_error(self):
        response = self.client.get('/api/zoho/auth/callback/')
        self.assertEqual(response.status_code, 400)
        self.assertIn("Authorization code is required", response.data["detail"])

    def test_zoho_oauth_callback_rejects_missing_state_error(self):
        response = self.client.get('/api/zoho/auth/callback/?code=mock_auth_code')
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid or expired OAuth login state", response.data["detail"])

    def test_zoho_oauth_callback_does_not_provision_unknown_user_error(self):
        self.employee.hard_delete()
        self.client.get('/api/zoho/auth/login-url/')
        state = self.client.session['zoho_oauth_state']
        response = self.client.get(f'/api/zoho/auth/callback/?code=mock_auth_code&state={state}')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['stage'], 'OAUTH_EMPLOYEE_LOOKUP')
        self.assertFalse(Employee.objects.filter(email='zoho.user@example.com').exists())

    def _callback(self, *, code='mock_auth_code'):
        self.client.get('/api/zoho/auth/login-url/')
        state = self.client.session['zoho_oauth_state']
        return self.client.get(f'/api/zoho/auth/callback/?code={code}&state={state}')

    @patch('zoho.views.ZohoAuthService.exchange_code_for_tokens')
    def test_callback_reports_token_exchange_failure_stage(self, exchange):
        exchange.side_effect = RuntimeError('token exchange unavailable')
        response = self._callback()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['stage'], 'OAUTH_TOKEN_EXCHANGE')
        self.assertEqual(response.data['error_type'], 'RuntimeError')

    @patch('zoho.views.ZohoAuthService.fetch_user_profile')
    @patch('zoho.views.ZohoAuthService.exchange_code_for_tokens')
    def test_callback_reports_profile_fetch_failure_stage(self, exchange, fetch):
        exchange.return_value = ('mock-access-token', 'https://accounts.zoho.com')
        fetch.side_effect = RuntimeError('profile endpoint unavailable')
        response = self._callback()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['stage'], 'OAUTH_PROFILE_FETCH')

    @patch('zoho.views.ZohoAuthService.fetch_user_profile')
    @patch('zoho.views.ZohoAuthService.exchange_code_for_tokens')
    def test_callback_rejects_missing_zoho_email(self, exchange, fetch):
        exchange.return_value = ('mock-access-token', 'https://accounts.zoho.com')
        fetch.return_value = {'email': None, 'zoho_user_id': 'zoho_usr_12345'}
        response = self._callback()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['stage'], 'OAUTH_EMAIL_VALIDATION')

    @patch('zoho.views.ZohoAuthService.fetch_user_profile')
    @patch('zoho.views.ZohoAuthService.exchange_code_for_tokens')
    def test_callback_without_zoho_user_id_matches_existing_email(self, exchange, fetch):
        exchange.return_value = ('mock-access-token', 'https://accounts.zoho.com')
        fetch.return_value = {'email': 'ZOHO.USER@example.com', 'zoho_user_id': None}
        response = self._callback()
        self.assertEqual(response.status_code, 200)
        self.employee.refresh_from_db()
        self.assertFalse(bool(self.employee.zoho_user_id))

    @patch('zoho.views.ZohoAuthService.fetch_user_profile')
    @patch('zoho.views.ZohoAuthService.exchange_code_for_tokens')
    def test_callback_rejects_employee_not_found(self, exchange, fetch):
        exchange.return_value = ('mock-access-token', 'https://accounts.zoho.com')
        fetch.return_value = {'email': 'missing@example.com', 'zoho_user_id': 'missing-id'}
        response = self._callback()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['stage'], 'OAUTH_EMPLOYEE_LOOKUP')

    @patch('zoho.views.ZohoAuthService.fetch_user_profile')
    @patch('zoho.views.ZohoAuthService.exchange_code_for_tokens')
    def test_callback_rejects_inactive_employee(self, exchange, fetch):
        self.employee.is_active = False
        self.employee.save(update_fields=['is_active'])
        exchange.return_value = ('mock-access-token', 'https://accounts.zoho.com')
        fetch.return_value = {'email': self.employee.email, 'zoho_user_id': 'zoho_usr_12345'}
        response = self._callback()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['stage'], 'OAUTH_EMPLOYEE_LOOKUP')

    @patch('zoho.views.ZohoAuthService.fetch_user_profile')
    @patch('zoho.views.ZohoAuthService.exchange_code_for_tokens')
    def test_callback_allows_matched_employee_without_company(self, exchange, fetch):
        self.employee.company = None
        self.employee.save(update_fields=['company'])
        exchange.return_value = ('mock-access-token', 'https://accounts.zoho.com')
        fetch.return_value = {'email': self.employee.email, 'zoho_user_id': 'zoho_usr_12345'}
        response = self._callback()
        self.assertEqual(response.status_code, 200)

    @override_settings(ZOHO_ALLOWED_EMAIL_DOMAIN='allowed.example')
    @patch('zoho.views.ZohoAuthService.fetch_user_profile')
    @patch('zoho.views.ZohoAuthService.exchange_code_for_tokens')
    def test_callback_rejects_disallowed_email_domain(self, exchange, fetch):
        exchange.return_value = ('mock-access-token', 'https://accounts.zoho.com')
        fetch.return_value = {'email': 'zoho.user@example.com', 'zoho_user_id': 'zoho_usr_12345'}
        response = self._callback()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['stage'], 'OAUTH_EMAIL_VALIDATION')
