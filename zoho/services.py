import os
import uuid

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail

from core.models import Company, Employee
from zoho.models import WorkDriveFolder, EmployeeDocument, EmailLog

MOCK_ACCESS_TOKEN = 'mock-access-token'


def _use_mock():
    return getattr(settings, 'ZOHO_USE_MOCK', False)


def get_zoho_config():
    """Return Zoho configuration values from Django settings."""
    use_mock = _use_mock()
    config = {
        'client_id': getattr(settings, 'ZOHO_CLIENT_ID', '') or os.getenv('ZOHO_CLIENT_ID', ''),
        'client_secret': getattr(settings, 'ZOHO_CLIENT_SECRET', '') or os.getenv('ZOHO_CLIENT_SECRET', ''),
        'refresh_token': getattr(settings, 'ZOHO_REFRESH_TOKEN', '') or os.getenv('ZOHO_REFRESH_TOKEN', ''),
        'org_id': getattr(settings, 'ZOHO_ORG_ID', '') or os.getenv('ZOHO_ORG_ID', ''),
        'use_mock': use_mock,
    }
    if not use_mock:
        required = ('client_id', 'client_secret', 'refresh_token')
        missing = [key for key in required if not config[key]]
        if missing:
            raise ImproperlyConfigured(
                f"Missing required Zoho settings: {', '.join(missing)}"
            )
    return config


def get_zoho_access_token():
    """Return a Zoho OAuth access token, or a mock token when mock mode is enabled."""
    if _use_mock():
        return MOCK_ACCESS_TOKEN
    service = ZohoWorkDriveService()
    return service._refresh_access_token()


def get_zoho_auth_headers():
    """Generate request headers containing a valid Zoho OAuth access token."""
    config = get_zoho_config()
    token = get_zoho_access_token()
    if config['use_mock']:
        headers = {'Authorization': f'Bearer {token}'}
        if config['org_id']:
            headers['X-Org-Id'] = config['org_id']
        return headers
    return {'Authorization': f'Zoho-oauthtoken {token}'}


class ZohoWorkDriveService:
    """
    Handles API communication with Zoho WorkDrive.
    Implements OAuth 2.0 Token Refresh, Folder Creation, and File Uploads.
    """

    def __init__(self):
        self.client_id = os.environ.get('ZOHO_CLIENT_ID')
        self.client_secret = os.environ.get('ZOHO_CLIENT_SECRET')
        self.refresh_token = os.environ.get('ZOHO_REFRESH_TOKEN')
        self.accounts_url = os.environ.get('ZOHO_ACCOUNTS_URL', 'https://accounts.zoho.com').rstrip('/')
        self.api_url = os.environ.get('ZOHO_WORKDRIVE_API_URL', 'https://workdrive.zoho.com/api/v1').rstrip('/')
        self.upload_url = os.environ.get(
            'ZOHO_WORKDRIVE_UPLOAD_URL', 'https://upload.zoho.com/api/v1/workdrive'
        ).rstrip('/')
        self.org_id = os.environ.get('ZOHO_ORG_ID', '')
        self._access_token = None

    def _refresh_access_token(self):
        """Exchanges the refresh token for a new access token (valid for 1 hour)."""
        if _use_mock():
            self._access_token = MOCK_ACCESS_TOKEN
            return self._access_token

        url = f"{self.accounts_url}/oauth/v2/token"
        payload = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
        }
        response = requests.post(url, data=payload)
        response.raise_for_status()
        data = response.json()
        self._access_token = data['access_token']
        return self._access_token

    def _get_headers(self):
        """Returns standard headers containing authorization token."""
        if not self._access_token:
            self._refresh_access_token()
        return {
            'Authorization': f"Zoho-oauthtoken {self._access_token}",
            'Accept': 'application/vnd.api+json',
        }

    def create_folder(
        self,
        company: Company,
        folder_name: str,
        parent_zoho_folder_id: str = None,
        created_by: Employee = None,
        employee: Employee = None,
    ) -> WorkDriveFolder:
        """Creates a folder in Zoho WorkDrive and registers its metadata in PostgreSQL."""
        if _use_mock():
            zoho_folder_id = f'mock_fld_{uuid.uuid4().hex[:12]}'
        else:
            url = f"{self.api_url}/folders"
            payload = {
                "data": {
                    "attributes": {"name": folder_name},
                    "type": "folders",
                }
            }
            if parent_zoho_folder_id:
                payload["data"]["attributes"]["parent_id"] = parent_zoho_folder_id

            headers = self._get_headers()
            headers['Content-Type'] = 'application/vnd.api+json'

            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            zoho_folder_id = data["data"]["id"]

        return WorkDriveFolder.objects.create(
            company=company,
            folder_name=folder_name,
            zoho_folder_id=zoho_folder_id,
            employee=employee,
            created_by=created_by,
        )

    def upload_document(
        self,
        employee: Employee,
        folder: WorkDriveFolder,
        document_name: str,
        document_type: str,
        file_content: bytes,
        uploaded_by: Employee = None,
    ) -> EmployeeDocument:
        """Uploads a file to Zoho WorkDrive and registers its metadata in PostgreSQL."""
        if _use_mock():
            zoho_file_id = f'mock_file_{uuid.uuid4().hex[:12]}'
        else:
            url = f"{self.upload_url}/files"
            token = self._access_token or self._refresh_access_token()
            headers = {'Authorization': f"Zoho-oauthtoken {token}"}
            files = {'content': (document_name, file_content)}
            data = {
                'parent_id': folder.zoho_folder_id,
                'filename': document_name,
                'override-name-exist': 'true',
            }
            response = requests.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
            res_data = response.json()
            zoho_file_id = res_data["data"][0]["id"]

        return EmployeeDocument.objects.create(
            company=employee.company,
            employee=employee,
            folder=folder,
            document_name=document_name,
            document_type=document_type,
            zoho_file_id=zoho_file_id,
            uploaded_by=uploaded_by or employee,
        )


class ZohoMailService:
    """Sends emails using Django SMTP and logs them in PostgreSQL."""

    @staticmethod
    def send_and_log_email(
        company: Company,
        recipient: str,
        subject: str,
        body: str,
        template_name: str,
        sent_by: Employee = None,
    ) -> EmailLog:
        """Send an email and record the result in PostgreSQL."""
        if _use_mock():
            status = 'SENT'
        else:
            try:
                sent_count = send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    fail_silently=False,
                )
                status = 'SENT' if sent_count > 0 else 'FAILED'
            except Exception as e:
                status = f'FAILED: {str(e)[:25]}'

        return EmailLog.objects.create(
            company=company,
            recipient=recipient,
            subject=subject,
            template_name=template_name,
            status=status,
            sent_by=sent_by,
        )
