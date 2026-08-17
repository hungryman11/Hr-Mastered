import logging
import re
import secrets
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from rest_framework.response import Response

from zoho.services import get_zoho_config

logger = logging.getLogger(__name__)


def _safe_oauth_error_message(exc: Exception) -> str:
    """Prevent credential-like query values from reaching logs or API responses."""
    message = str(exc)[:1000]
    return re.sub(
        r'(?i)(code|state|client_secret|access_token|refresh_token)=([^\s&]+)',
        r'\1=[redacted]',
        message,
    )


def _oauth_failure_response(stage: str, exc: Exception, *, http_status: int = 400) -> Response:
    """Log a staged OAuth failure while preserving validation details for expected errors."""
    safe_message = _safe_oauth_error_message(exc)
    logger.exception(
        'Zoho OAuth callback failed: stage=%s exception_type=%s exception_message=%s',
        stage,
        exc.__class__.__name__,
        safe_message,
    )

    if isinstance(exc, ValueError):
        return Response({
            'detail': str(exc),
            'stage': stage,
        }, status=http_status)

    if settings.DEBUG:
        return Response({
            'detail': 'Zoho login failed',
            'stage': stage,
            'error_type': exc.__class__.__name__,
            'error': safe_message,
        }, status=http_status)
    return Response({'detail': 'Zoho login could not be completed.'}, status=http_status)


def home_view(request):
    config = get_zoho_config()
    return render(request, 'home.html', {
        'mock_mode': config.get('use_mock', False),
    })


def zoho_demo_view(request):
    config = get_zoho_config()
    return JsonResponse({
        "mock_mode": config.get("use_mock", False),
    })


def zoho_oauth_callback_view(request):
    return HttpResponse('<h1>OAuth callback</h1><p>Please complete sign-in through the HR platform.</p>')


from django.contrib.auth import login
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from zoho.services import ZohoAuthService, validate_redirect_uri
from core.serializers import EmployeeSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def zoho_login_url_api_view(request):
    redirect_uri = request.query_params.get('redirect_uri') or settings.ZOHO_OAUTH_REDIRECT_URI
    try:
        validated_redirect_uri = validate_redirect_uri(redirect_uri)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    state = secrets.token_urlsafe(32)
    request.session['zoho_oauth_state'] = state
    request.session['zoho_oauth_redirect_uri'] = validated_redirect_uri
    request.session.set_expiry(600)

    request.session.save()

    login_url = ZohoAuthService.get_authorization_url(validated_redirect_uri, state)
    parsed_login_url = urlsplit(login_url)
    authorization_params = parse_qs(parsed_login_url.query)
    # Temporary authorization-request diagnostics. The generated URL itself and
    # OAuth state are intentionally not logged.
    logger.info(
        'Zoho authorization request: hostname=%s client_id=%s redirect_uri=%s '
        'scope=%s response_type=%s access_type=%s prompt=%s',
        parsed_login_url.hostname,
        authorization_params.get('client_id', [''])[0],
        authorization_params.get('redirect_uri', [''])[0],
        authorization_params.get('scope', [''])[0],
        authorization_params.get('response_type', [''])[0],
        authorization_params.get('access_type', [''])[0],
        authorization_params.get('prompt', [''])[0],
    )

    return Response({
        "login_url": login_url,
        "redirect_uri": validated_redirect_uri,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def zoho_oauth_login_callback_api_view(request):
    code = request.query_params.get('code')
    state = request.query_params.get('state')
    redirect_uri = request.query_params.get('redirect_uri')
    expected_state = request.session.pop('zoho_oauth_state', None)
    expected_redirect_uri = request.session.pop('zoho_oauth_redirect_uri', None)

    logger.info("Zoho OAuth callback reached Django: code_present=%s", bool(code))

    if not code:
        return _oauth_failure_response(
            'OAUTH_STATE_VALIDATION', ValueError('Authorization code is required.')
        )
    if not state:
        return _oauth_failure_response(
            'OAUTH_STATE_VALIDATION', ValueError('Invalid or expired OAuth login state.')
        )
    if not expected_state or not secrets.compare_digest(state, expected_state):
        return _oauth_failure_response(
            'OAUTH_STATE_VALIDATION', ValueError('Invalid or expired OAuth login state.')
        )

    try:
        validated_redirect_uri = validate_redirect_uri(redirect_uri, default=expected_redirect_uri or settings.ZOHO_OAUTH_REDIRECT_URI)
    except ValueError as exc:
        return _oauth_failure_response('OAUTH_STATE_VALIDATION', exc)

    if expected_redirect_uri and validated_redirect_uri != expected_redirect_uri:
        return _oauth_failure_response(
            'OAUTH_STATE_VALIDATION',
            ValueError('Redirect URI does not match the login request.'),
        )

    try:
        access_token, accounts_url = ZohoAuthService.exchange_code_for_tokens(
            code, validated_redirect_uri
        )
    except Exception as exc:
        return _oauth_failure_response('OAUTH_TOKEN_EXCHANGE', exc)

    try:
        profile = ZohoAuthService.fetch_user_profile(access_token, accounts_url)
    except Exception as exc:
        return _oauth_failure_response('OAUTH_PROFILE_FETCH', exc)

    try:
        email, zoho_user_id = ZohoAuthService.validate_profile_email(profile)
    except Exception as exc:
        return _oauth_failure_response('OAUTH_EMAIL_VALIDATION', exc)

    try:
        employee = ZohoAuthService.find_existing_employee(email, zoho_user_id)
        logger.info(
            'Zoho employee lookup: match_found=%s active=%s company_present=%s '
            'employee_zoho_identity_present=%s profile_zoho_identity_present=%s',
            True,
            employee.is_active and not bool(employee.deleted_at),
            bool(employee.company_id),
            bool(employee.zoho_user_id),
            bool(zoho_user_id),
        )
        employee = ZohoAuthService.validate_employee_identity(employee, zoho_user_id)
    except Exception as exc:
        return _oauth_failure_response('OAUTH_EMPLOYEE_LOOKUP', exc)

    try:
        employee.backend = (settings.AUTHENTICATION_BACKENDS[0]
                            if getattr(settings, 'AUTHENTICATION_BACKENDS', None)
                            else 'django.contrib.auth.backends.ModelBackend')
        login(request, employee)
        return Response({
            'detail': 'Successfully logged in with Zoho Mail.',
            'employee': EmployeeSerializer(employee, context={'request': request}).data,
        }, status=status.HTTP_200_OK)
    except Exception as exc:
        return _oauth_failure_response('OAUTH_DJANGO_LOGIN', exc)



