import os
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.views import View


class PortalIndexView(View):
    """Serves the React SPA compiled index.html for all /app/* routes."""

    def get(self, request, *args, **kwargs):
        dist_path = settings.BASE_DIR / 'frontend' / 'dist' / 'index.html'
        if os.path.exists(dist_path):
            with open(dist_path, 'r', encoding='utf-8') as f:
                return HttpResponse(f.read(), content_type='text/html')

        fallback_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HR Platform Portal</title>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap">
    <style>
        body { margin: 0; background: #0b0f19; color: #f1f5f9; font-family: 'Inter', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; text-align: center; }
        .card { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(16px); padding: 40px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); max-width: 450px; }
        h1 { margin-top: 0; color: #6366f1; }
        a { color: #818cf8; text-decoration: none; font-weight: 500; }
        .btn { display: inline-block; margin-top: 20px; padding: 12px 24px; background: #6366f1; color: white; border-radius: 8px; font-weight: 600; text-decoration: none; }
    </style>
</head>
<body>
    <div class="card">
        <h1>HR Portal</h1>
        <p>The React front-end source files are installed in <code>frontend/</code>.</p>
        <p>Run <code>npm run build</code> inside the <code>frontend/</code> directory to compile the production bundle.</p>
        <a href="/api/zoho/login/" class="btn">Sign in with Zoho Mail</a>
    </div>
</body>
</html>"""
        return HttpResponse(fallback_html, content_type='text/html')
