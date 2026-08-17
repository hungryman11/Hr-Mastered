import os
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError


def _is_truthy(value):
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _csv_values(value):
    if value is None:
        return []
    return [item.strip() for item in str(value).split(',') if item.strip()]


class Command(BaseCommand):
    help = 'Validate that the environment is safe for production deployment.'

    def add_arguments(self, parser):
        parser.add_argument('--strict', action='store_true', help='Fail on any non-blocking warnings.')

    def _pass(self, label, detail=''):
        self.stdout.write(f'PASS {label}' + (f' - {detail}' if detail else ''))

    def _fail(self, label, detail=''):
        self.stdout.write(f'FAIL {label}' + (f' - {detail}' if detail else ''))

    def _check(self, label, condition, detail=''):
        if condition:
            self._pass(label, detail)
            return True
        self._fail(label, detail)
        return False

    def handle(self, *args, **options):
        issues = []

        env = os.environ
        app_env = (env.get('APP_ENV', 'development') or 'development').strip().lower()
        is_production = app_env in {'production', 'prod', 'live'}

        if not is_production:
            self.stdout.write('INFO APP_ENV is not production; validation is running in local-safe mode.')

        # Core security
        secret_key = env.get('SECRET_KEY', '').strip()
        if self._check('SECRET_KEY configured', bool(secret_key) and not secret_key.lower().startswith('django-insecure') and len(secret_key) >= 50 and len(set(secret_key)) >= 5):
            pass
        else:
            issues.append('SECRET_KEY missing or unsafe')

        field_key = env.get('FIELD_ENCRYPTION_KEY', '').strip()
        if self._check('FIELD_ENCRYPTION_KEY configured', bool(field_key) and len(field_key) >= 32):
            pass
        else:
            issues.append('FIELD_ENCRYPTION_KEY missing or too short')

        debug = _is_truthy(env.get('DEBUG', 'False'))
        self._check('DEBUG disabled', not debug or not is_production, 'DEBUG must be False for production deployment.')
        if is_production and debug:
            issues.append('DEBUG is enabled in production')

        ssl_redirect = _is_truthy(env.get('SECURE_SSL_REDIRECT', 'False'))
        self._check('HTTPS enforced', (not is_production) or ssl_redirect, 'SECURE_SSL_REDIRECT must be True in production.')
        if is_production and not ssl_redirect:
            issues.append('SECURE_SSL_REDIRECT not enabled')

        session_secure = _is_truthy(env.get('SESSION_COOKIE_SECURE', 'False'))
        csrf_secure = _is_truthy(env.get('CSRF_COOKIE_SECURE', 'False'))
        self._check('Secure cookies enabled', (not is_production) or (session_secure and csrf_secure), 'SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE must both be True in production.')
        if is_production and not (session_secure and csrf_secure):
            issues.append('secure cookies not enabled')

        hsts_seconds = int(env.get('SECURE_HSTS_SECONDS', '0') or '0')
        self._check('HSTS configured', (not is_production) or hsts_seconds > 0, 'SECURE_HSTS_SECONDS must be set in production.')
        if is_production and hsts_seconds <= 0:
            issues.append('SECURE_HSTS_SECONDS missing or zero')

        # Database
        database_url = env.get('DATABASE_URL', '').strip()
        parsed = urlparse(database_url)
        database_ok = bool(parsed.scheme and parsed.scheme.startswith('postgres')) and bool(parsed.hostname)
        self._check('DATABASE configured', database_ok or not is_production, 'DATABASE_URL must point to Postgres in production.')
        if is_production and not database_ok:
            issues.append('DATABASE_URL missing or invalid')

        # Host and CSRF allow-lists
        allowed_hosts = _csv_values(env.get('ALLOWED_HOSTS'))
        if is_production:
            self._check('ALLOWED_HOSTS configured', bool(allowed_hosts) and '*' not in allowed_hosts, 'Set ALLOWED_HOSTS to real production hosts only.')
            if not allowed_hosts or '*' in allowed_hosts:
                issues.append('ALLOWED_HOSTS invalid')
        else:
            self._check('ALLOWED_HOSTS local dev safe', True, 'Local development hosts are allowed.')

        csrf_origins = _csv_values(env.get('CSRF_TRUSTED_ORIGINS'))
        if is_production:
            self._check('CSRF_TRUSTED_ORIGINS configured', bool(csrf_origins) and all(origin.startswith('https://') for origin in csrf_origins), 'Use HTTPS-only trusted origins in production.')
            if not csrf_origins or any(not origin.startswith('https://') for origin in csrf_origins):
                issues.append('CSRF_TRUSTED_ORIGINS invalid')
        else:
            self._check('CSRF local dev safe', True, 'Local Vite origins are allowed in development.')

        # Zoho
        zoho_fields = {
            'ZOHO_CLIENT_ID': env.get('ZOHO_CLIENT_ID', '').strip(),
            'ZOHO_CLIENT_SECRET': env.get('ZOHO_CLIENT_SECRET', '').strip(),
            'ZOHO_REFRESH_TOKEN': env.get('ZOHO_REFRESH_TOKEN', '').strip(),
            'ZOHO_OAUTH_REDIRECT_URI': env.get('ZOHO_OAUTH_REDIRECT_URI', '').strip(),
            'ZOHO_ALLOWED_REDIRECT_URIS': env.get('ZOHO_ALLOWED_REDIRECT_URIS', '').strip(),
        }
        for name, value in zoho_fields.items():
            label = name.replace('_', ' ')
            result = bool(value)
            if is_production:
                self._check(f'{name} configured', result, f'{name} is required in production.')
                if not result:
                    issues.append(f'{name} missing')
            else:
                self._check(f'{name} local safe', True, 'Local development may omit it.')

        # Email
        email_fields = {
            'EMAIL_HOST': env.get('EMAIL_HOST', '').strip(),
            'EMAIL_HOST_USER': env.get('EMAIL_HOST_USER', '').strip(),
            'EMAIL_HOST_PASSWORD': env.get('EMAIL_HOST_PASSWORD', '').strip(),
            'DEFAULT_FROM_EMAIL': env.get('DEFAULT_FROM_EMAIL', '').strip(),
        }
        for name, value in email_fields.items():
            result = bool(value)
            if is_production:
                self._check(f'{name} configured', result, f'{name} is required in production.')
                if not result:
                    issues.append(f'{name} missing')

        # Storage / required app configuration
        media_root = env.get('MEDIA_ROOT', '').strip()
        if is_production:
            self._check('MEDIA_ROOT configured', bool(media_root), 'Set MEDIA_ROOT for production uploads.')
            if not media_root:
                issues.append('MEDIA_ROOT missing')
        else:
            self._check('media configuration local-safe', True, 'Local storage is acceptable in development.')

        if not issues:
            self.stdout.write(self.style.SUCCESS('Production validation passed.'))
            return

        summary = '; '.join(issues)
        raise CommandError(f'Production validation failed: {summary}')
