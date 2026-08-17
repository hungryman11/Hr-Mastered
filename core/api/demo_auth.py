"""DEBUG-only local session entry point for the isolated UAT dataset."""

from django.conf import settings
from django.contrib.auth import login
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from core.models import Employee


DEMO_COMPANY = 'Infinity Microfinance Bank — DEMO'


def _disabled():
    return JsonResponse({'detail': 'Demo login is unavailable.'}, status=404)


@require_GET
@ensure_csrf_cookie
def demo_login_users(request):
    if not settings.DEBUG:
        return _disabled()
    csrf_token = get_token(request)
    users = Employee.objects.filter(company__name=DEMO_COMPANY, username__startswith='demo.', is_active=True).order_by('username')
    # The masked token is safe to return to this same-origin DEBUG page. Django
    # still validates it against the CSRF cookie on every state-changing request.
    return JsonResponse({
        'users': [{'username': user.username, 'role': user.role} for user in users],
        'csrf_token': csrf_token,
    })


@require_POST
def demo_login(request):
    if not settings.DEBUG:
        return _disabled()
    import json
    try:
        # Contract: application/json with a seeded ``username``. This local,
        # DEBUG-only role selector deliberately does not use a password.
        username = str(json.loads(request.body or '{}').get('username') or '')
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'detail': 'Invalid request.'}, status=400)
    user = Employee.objects.filter(company__name=DEMO_COMPANY, username=username, is_active=True).first()
    if not user:
        return JsonResponse({'detail': 'Unknown demo user.'}, status=404)
    login(request, user)
    return JsonResponse({'detail': 'Demo session created.', 'username': user.username, 'role': user.role})
