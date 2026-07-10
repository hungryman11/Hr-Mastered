import os
import requests
from django.conf import settings
from django.core.mail import send_mail
from core.models import Company, Employee
from zoho.models import WorkDriveFolder, EmployeeDocument, EmailLog

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
        # Note: Zoho WorkDrive uses a separate sub-domain/upload endpoint for file uploads
        self.upload_url = os.environ.get('ZOHO_WORKDRIVE_UPLOAD_URL', 'https://upload.zoho.com/api/v1/workdrive').rstrip('/')
        self._access_token = None

    def _refresh_access_token(self):
        """Exchanges the refresh token for a new access token (valid for 1 hour)."""
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

    def create_folder(self, company: Company, folder_name: str, parent_zoho_folder_id: str = None, created_by: Employee = None) -> WorkDriveFolder:
        """
        Creates a folder in Zoho WorkDrive and registers its metadata in the PostgreSQL database.
        
        Args:
            company: The tenant Company scope.
            folder_name: The name of the folder (e.g., 'EMP0001', 'Recruitment').
            parent_zoho_folder_id: Optional parent folder ID in Zoho.
            created_by: The Employee initiating the creation.
        """
        url = f"{self.api_url}/folders"
        
        payload = {
            "data": {
                "attributes": {
                    "name": folder_name
                },
                "type": "folders"
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
        
        # Log to PostgreSQL
        db_folder = WorkDriveFolder.objects.create(
            company=company,
            folder_name=folder_name,
            zoho_folder_id=zoho_folder_id,
            created_by=created_by
        )
        return db_folder

    def upload_document(self, employee: Employee, folder: WorkDriveFolder, document_name: str, document_type: str, file_content: bytes, uploaded_by: Employee = None) -> EmployeeDocument:
        """
        Uploads a file to Zoho WorkDrive and registers its metadata in PostgreSQL.
        
        Args:
            employee: The Employee owner of the document.
            folder: The target WorkDriveFolder database object.
            document_name: The physical filename (e.g., 'Passport.pdf').
            document_type: The document type metadata (e.g., 'PASSPORT', 'CV').
            file_content: File bytes.
            uploaded_by: The Employee performing the upload.
        """
        url = f"{self.upload_url}/files"
        
        # Ensure we have a valid token
        token = self._access_token or self._refresh_access_token()
        headers = {
            'Authorization': f"Zoho-oauthtoken {token}",
        }
        
        files = {
            'content': (document_name, file_content),
        }
        
        data = {
            'parent_id': folder.zoho_folder_id,
            'filename': document_name,
            'override-name-exist': 'true'
        }
        
        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()
        res_data = response.json()
        
        # Extract the file ID from the Zoho API response structure
        zoho_file_id = res_data["data"][0]["id"]
        
        # Log to PostgreSQL
        doc = EmployeeDocument.objects.create(
            company=employee.company,
            employee=employee,
            folder=folder,
            document_name=document_name,
            document_type=document_type,
            zoho_file_id=zoho_file_id,
            uploaded_by=uploaded_by or employee
        )
        return doc


class ZohoMailService:
    """
    Sends emails using Django's SMTP backend (pointing to Zoho SMTP) and logs them in PostgreSQL.
    """
    @staticmethod
    def send_and_log_email(company: Company, recipient: str, subject: str, body: str, template_name: str, sent_by: Employee = None) -> EmailLog:
        """
        Sends an email using standard Django SMTP and records the result in PostgreSQL.
        """
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
            
        # Log to PostgreSQL
        log = EmailLog.objects.create(
            company=company,
            recipient=recipient,
            subject=subject,
            template_name=template_name,
            status=status,
            sent_by=sent_by
        )
        return log
# Helper functions for easy access in views

def get_zoho_config():
    """Return Zoho configuration values from environment variables.
    Includes client ID, secret, refresh token, org ID, and mock mode flag.
    """
    return {
        'client_id': os.getenv('ZOHO_CLIENT_ID', ''),
        'client_secret': os.getenv('ZOHO_CLIENT_SECRET', ''),
        'refresh_token': os.getenv('ZOHO_REFRESH_TOKEN', ''),
        'org_id': os.getenv('ZOHO_ORG_ID', ''),
        'use_mock': os.getenv('ZOHO_USE_MOCK', 'False').lower() in ('1', 'true', 'yes', 'on'),
    }

def get_zoho_auth_headers():
    """Generate request headers containing a valid Zoho OAuth access token.
    This utilizes ZohoWorkDriveService to refresh the token when needed.
    """
    service = ZohoWorkDriveService()
    token = service._refresh_access_token()
    return {'Authorization': f'Zoho-oauthtoken {token}'}
