import logging
import os
import uuid
from urllib.parse import urlencode, urlsplit, urlunsplit

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail

from django.db import models
from core.models import Company, Employee
from zoho.models import WorkDriveFolder, EmployeeDocument, EmailLog

MOCK_ACCESS_TOKEN = 'mock-access-token'
MOCK_AUTH_CODE = 'mock_auth_code'
ZOHO_REQUEST_TIMEOUT_SECONDS = 15
logger = logging.getLogger(__name__)


class ZohoTokenExchangeError(Exception):
    """A safe-to-display failure response from Zoho's token endpoint."""

    def __init__(self, status_code: int, response_body: str):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f'Zoho token exchange failed with HTTP {status_code}: {response_body}')


def _use_mock():
    return getattr(settings, 'ZOHO_USE_MOCK', False)


def get_zoho_config():
    """Return Zoho configuration values from Django settings."""
    use_mock = _use_mock()
    config = {
        'client_id': getattr(settings, 'ZOHO_CLIENT_ID', ''),
        'client_secret': getattr(settings, 'ZOHO_CLIENT_SECRET', ''),
        'refresh_token': getattr(settings, 'ZOHO_REFRESH_TOKEN', ''),
        'org_id': getattr(settings, 'ZOHO_ORG_ID', ''),
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


def _get_allowed_redirect_uris():
    configured = getattr(settings, 'ZOHO_ALLOWED_REDIRECT_URIS', '') or getattr(settings, 'ZOHO_OAUTH_REDIRECT_URI', '')
    raw_values = [value.strip() for value in configured.split(',') if value.strip()]
    if not raw_values:
        raise ImproperlyConfigured('ZOHO_ALLOWED_REDIRECT_URIS must include at least one registered redirect URI.')
    return [normalize_redirect_uri(value) for value in raw_values]


def normalize_redirect_uri(redirect_uri: str) -> str:
    if not redirect_uri:
        raise ValueError('A redirect URI is required.')
    parsed = urlsplit(redirect_uri)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise ValueError('Redirect URI must be an absolute http(s) URL.')
    path = parsed.path or '/'
    if path != '/' and path.endswith('/'):
        path = path.rstrip('/')
    return urlunsplit((parsed.scheme, parsed.netloc, path, '', ''))


def validate_redirect_uri(redirect_uri: str | None, *, default: str | None = None) -> str:
    candidate = redirect_uri or default or getattr(settings, 'ZOHO_OAUTH_REDIRECT_URI', '')
    if not candidate:
        raise ValueError('A redirect URI is required.')
    normalized = normalize_redirect_uri(candidate)
    allowed = _get_allowed_redirect_uris()
    if normalized not in allowed:
        raise ValueError('Redirect URI is not registered for this Zoho integration.')
    return normalized


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
        response = requests.post(url, data=payload, timeout=ZOHO_REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        self._access_token = data['access_token']
        return self._access_token

    def _get_headers(self):
        """Returns standard headers containing authorization token."""
        if not self._access_token:
            self._refresh_access_token()
        headers = {
            'Authorization': f"Zoho-oauthtoken {self._access_token}",
            'Accept': 'application/vnd.api+json',
        }
        if self.org_id:
            headers['X-ORG-ID'] = self.org_id
        return headers

    def create_folder(
        self,
        company: Company,
        folder_name: str,
        parent_zoho_folder_id: str = None,
        created_by: Employee = None,
        employee: Employee = None,
    ) -> WorkDriveFolder:
        """Creates a folder in Zoho WorkDrive and registers its metadata in PostgreSQL."""
        existing = WorkDriveFolder.objects.filter(employee=employee).first() if employee else None
        if existing:
            return existing
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

            response = requests.post(url, json=payload, headers=headers, timeout=ZOHO_REQUEST_TIMEOUT_SECONDS)
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
            headers = self._get_headers()
            files = {'content': (document_name, file_content)}
            data = {
                'parent_id': folder.zoho_folder_id,
                'filename': document_name,
                'override-name-exist': 'true',
            }
            response = requests.post(url, headers=headers, files=files, data=data, timeout=ZOHO_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            res_data = response.json()
            zoho_file_id = res_data["data"][0]["id"]

        document, _ = EmployeeDocument.objects.update_or_create(
            zoho_file_id=zoho_file_id,
            defaults={
                'company': employee.company,
                'employee': employee,
                'folder': folder,
                'document_name': document_name,
                'document_type': document_type,
                'uploaded_by': uploaded_by or employee,
            },
        )
        return document

    def find_file_by_name(self, folder_id: str, document_name: str) -> str | None:
        """Find an existing file by name in a WorkDrive folder. Returns zoho_file_id if found, else None."""
        if _use_mock():
            existing_doc = EmployeeDocument.objects.filter(folder__zoho_folder_id=folder_id, document_name=document_name).first()
            return existing_doc.zoho_file_id if existing_doc else None

        try:
            url = f"{self.api_url}/folders/{folder_id}/files"
            headers = self._get_headers()
            response = requests.get(url, headers=headers, timeout=ZOHO_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            data = response.json()
            for item in data.get("data", []):
                if item.get("attributes", {}).get("name") == document_name:
                    return item.get("id")
        except Exception:
            pass
        return None

    def delete_file(self, zoho_file_id: str) -> bool:
        """Deletes a file from Zoho WorkDrive."""
        if _use_mock():
            EmployeeDocument.objects.filter(zoho_file_id=zoho_file_id).delete()
            return True
        try:
            url = f"{self.api_url}/files/{zoho_file_id}"
            headers = self._get_headers()
            response = requests.delete(url, headers=headers, timeout=ZOHO_REQUEST_TIMEOUT_SECONDS)
            return response.status_code in (200, 204)
        except Exception:
            return False



class ZohoAuthService:
    """Handles Zoho OAuth 2.0 User Login / Zoho Mail authentication flow."""

    @staticmethod
    def get_authorization_url(redirect_uri: str, state: str = None) -> str:
        validated_redirect_uri = validate_redirect_uri(redirect_uri)
        if _use_mock():
            # Skip the real accounts.zoho.com screen entirely. Simulate what Zoho would
            # do at the end of a real login: redirect the browser straight back to our
            # own redirect_uri with a code + state. exchange_code_for_user_profile()
            # already short-circuits on this exact code, so the rest of the flow
            # (OAuthCallback -> /zoho/auth/callback/) runs completely unchanged. This
            # lets the whole login flow be built/tested with zero real Zoho app/access.
            params = {'code': MOCK_AUTH_CODE}
            if state:
                params['state'] = state
            return f"{validated_redirect_uri}?{urlencode(params)}"
        client_id = getattr(settings, 'ZOHO_CLIENT_ID', '')
        accounts_url = getattr(settings, 'ZOHO_ACCOUNTS_URL', os.environ.get('ZOHO_ACCOUNTS_URL', 'https://accounts.zoho.com')).rstrip('/')
        params = {
            'scope': getattr(settings, 'ZOHO_LOGIN_SCOPES', 'AaaServer.profile.READ'),
            'client_id': client_id,
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent',
            'redirect_uri': validated_redirect_uri,
        }
        if state:
            params['state'] = state
        return f"{accounts_url}/oauth/v2/auth?{urlencode(params)}"

    @staticmethod
    def exchange_code_for_user_profile(code: str, redirect_uri: str) -> dict:
        """Compatibility wrapper for the authorization-code and profile flow."""
        validated_redirect_uri = validate_redirect_uri(redirect_uri)
        if _use_mock() or code == 'mock_auth_code':
            return {
                'email': 'zoho.user@example.com',
                'first_name': 'Zoho',
                'last_name': 'User',
                'zoho_user_id': 'zoho_usr_12345',
            }

        access_token, accounts_url = ZohoAuthService.exchange_code_for_tokens(
            code, validated_redirect_uri
        )
        return ZohoAuthService.fetch_user_profile(access_token, accounts_url)

    @staticmethod
    def exchange_code_for_tokens(code: str, redirect_uri: str) -> tuple[str, str]:
        """Exchange an authorization code without exposing the received token."""
        validated_redirect_uri = validate_redirect_uri(redirect_uri)
        accounts_url = getattr(
            settings,
            'ZOHO_ACCOUNTS_URL',
            os.environ.get('ZOHO_ACCOUNTS_URL', 'https://accounts.zoho.com'),
        ).rstrip('/')
        if _use_mock() or code == 'mock_auth_code':
            return MOCK_ACCESS_TOKEN, accounts_url

        client_id = getattr(settings, 'ZOHO_CLIENT_ID', '')
        client_secret = getattr(settings, 'ZOHO_CLIENT_SECRET', '')

        token_url = f"{accounts_url}/oauth/v2/token"
        payload = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': validated_redirect_uri,
            'grant_type': 'authorization_code',
        }
        # Temporary OAuth diagnostics. Deliberately log presence flags rather than
        # credentials or authorization-code/token values.
        logger.info(
            'Zoho token exchange request: token_url=%s client_id=%s '
            'redirect_uri=%s grant_type=%s code_present=%s client_secret_present=%s',
            token_url,
            client_id,
            validated_redirect_uri,
            payload['grant_type'],
            bool(code),
            bool(client_secret),
        )
        try:
            res = requests.post(token_url, data=payload, timeout=10)
            res.raise_for_status()
        except requests.HTTPError as exc:
            response = exc.response
            status_code = response.status_code if response is not None else 0
            response_body = (response.text if response is not None else str(exc))[:2000]
            # Do not log response headers: they are not needed to diagnose this
            # redirect URI failure and can contain credentials in other scenarios.
            logger.error(
                'Zoho token exchange rejected: http_status=%s response_body=%s',
                status_code,
                response_body,
            )
            raise ZohoTokenExchangeError(status_code, response_body) from exc
        token_data = res.json()

        access_token = token_data.get('access_token')
        if not access_token:
            raise ValueError(f"Failed to obtain access token from Zoho: {token_data.get('error', 'Unknown error')}")

        return access_token, accounts_url

    @staticmethod
    def fetch_user_profile(access_token: str, accounts_url: str) -> dict:
        """Fetch and parse the Zoho profile, logging only non-identifying metadata."""
        if _use_mock() or access_token == MOCK_ACCESS_TOKEN:
            return {
                'email': 'zoho.user@example.com',
                'first_name': 'Zoho',
                'last_name': 'User',
                'zoho_user_id': 'zoho_usr_12345',
            }
        user_info_url = f"{accounts_url}/oauth/user/info"
        headers = {'Authorization': f"Zoho-oauthtoken {access_token}"}
        user_res = requests.get(user_info_url, headers=headers, timeout=10)
        user_res.raise_for_status()
        info = user_res.json()

        raw_email = info.get('Email') or info.get('email')
        normalized_email = raw_email.lower().strip() if isinstance(raw_email, str) else ''
        email_domain = normalized_email.rsplit('@', 1)[1] if '@' in normalized_email else ''
        raw_zoho_user_id = info.get('ZUID') or info.get('id')
        logger.info(
            'Zoho profile response: http_status=%s json_keys=%s email_present=%s '
            'email_domain=%s zoho_user_id_present=%s',
            user_res.status_code,
            sorted(str(key) for key in info.keys()),
            bool(normalized_email),
            email_domain,
            bool(raw_zoho_user_id),
        )

        return {
            'email': raw_email,
            'first_name': info.get('First_Name') or info.get('first_name', 'Zoho'),
            'last_name': info.get('Last_Name') or info.get('last_name', 'User'),
            'zoho_user_id': str(raw_zoho_user_id or uuid.uuid4().hex[:10]),
        }

    @staticmethod
    def authenticate_existing_user(profile: dict) -> Employee:
        """Authenticate only an active, pre-provisioned employee account."""
        email, zoho_user_id = ZohoAuthService.validate_profile_email(profile)
        employee = ZohoAuthService.find_existing_employee(email, zoho_user_id)
        return ZohoAuthService.validate_employee_identity(employee, zoho_user_id)

    @staticmethod
    def validate_profile_email(profile: dict) -> tuple[str, str | None]:
        """Normalize and allow-list a Zoho profile email without logging it."""
        email = profile.get('email')
        zoho_user_id = profile.get('zoho_user_id')
        if not email:
            raise ValueError('Email is required for Zoho login.')
        email = email.lower().strip()
        allowed_domain = getattr(settings, 'ZOHO_ALLOWED_EMAIL_DOMAIN', '')
        if allowed_domain and not email.endswith(f'@{allowed_domain}'):
            raise ValueError('This Zoho account is not allowed for this HR platform.')
        return email, zoho_user_id

    @staticmethod
    def find_existing_employee(email: str, zoho_user_id: str | None) -> Employee:
        """Find a pre-provisioned employee by Zoho identity or normalized email."""
        employee = Employee.objects.filter(
            models.Q(zoho_user_id=zoho_user_id) | models.Q(email=email)
        ).first()
        if not employee:
            raise ValueError('No active employee account is provisioned for this Zoho email address.')
        return employee

    @staticmethod
    def validate_employee_identity(employee: Employee, zoho_user_id: str | None) -> Employee:
        """Confirm the provisioned employee is eligible for this Zoho identity."""
        if not employee.is_active or employee.deleted_at:
            raise ValueError('This employee account is inactive.')
        if employee.zoho_user_id and zoho_user_id and employee.zoho_user_id != zoho_user_id:
            raise ValueError('This Zoho account does not match the provisioned employee account.')
        else:
            if not employee.zoho_user_id and zoho_user_id:
                employee.zoho_user_id = zoho_user_id
                employee.save(update_fields=['zoho_user_id', 'updated_at'])
        return employee


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
