from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from zoho.services import get_zoho_auth_headers, get_zoho_config


def home_view(request):
    config = get_zoho_config()
    headers = get_zoho_auth_headers()
    return render(request, 'home.html', {
        'mock_mode': config.get('use_mock', False),
        'client_id': config.get('client_id') or '',
        'org_id': config.get('org_id') or '',
        'headers': headers,
    })


def zoho_demo_view(request):
    config = get_zoho_config()
    headers = get_zoho_auth_headers()
    return JsonResponse({
        "mock_mode": config.get("use_mock", False),
        "client_id": config.get("client_id") or "",
        "org_id": config.get("org_id") or "",
        "headers": headers,
    })


def zoho_oauth_callback_view(request):
    """Display the OAuth authorization code from Zoho redirect."""
    code = request.GET.get('code', '')
    error = request.GET.get('error', '')
    if error:
        return HttpResponse(
            f"<h1>OAuth Error</h1><p>{error}</p>",
            content_type='text/html',
        )
    if not code:
        return HttpResponse(
            "<h1>OAuth Callback</h1><p>No authorization code received.</p>",
            content_type='text/html',
        )
    return HttpResponse(
        f"<h1>Authorization Code</h1>"
        f"<p>Copy this code into <code>get_refresh_token.py</code>:</p>"
        f"<pre>{code}</pre>",
        content_type='text/html',
    )
