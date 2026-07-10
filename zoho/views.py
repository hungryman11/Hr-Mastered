from django.http import JsonResponse
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
