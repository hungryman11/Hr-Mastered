import os
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from core.models import Company, Employee, EmployeeRole


class ProductionValidatorTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Acme Production Co')

    @override_settings(DEBUG=False)
    def test_validate_production_passes_for_valid_configuration(self):
        env = {
            'APP_ENV': 'production',
            'DEBUG': 'False',
            'SECRET_KEY': 'this-is-a-production-secret-key-that-is-long-enough-12345',
            'FIELD_ENCRYPTION_KEY': 'kPr5nW6Vf1Q0yJj0sD73xXx0rXJbM1Jc0A0h1Z0u4aI=',
            'DATABASE_URL': 'postgres://user:pass@localhost:5432/hr_prod',
            'ALLOWED_HOSTS': 'app.example.com,api.example.com',
            'CSRF_TRUSTED_ORIGINS': 'https://app.example.com,https://api.example.com',
            'SECURE_SSL_REDIRECT': 'True',
            'SESSION_COOKIE_SECURE': 'True',
            'CSRF_COOKIE_SECURE': 'True',
            'SECURE_HSTS_SECONDS': '31536000',
            'ZOHO_CLIENT_ID': 'zoho-client-id',
            'ZOHO_CLIENT_SECRET': 'zoho-client-secret',
            'ZOHO_REFRESH_TOKEN': 'zoho-refresh-token',
            'ZOHO_ORG_ID': 'zoho-org-id',
            'ZOHO_OAUTH_REDIRECT_URI': 'https://app.example.com/app/callback',
            'ZOHO_ALLOWED_REDIRECT_URIS': 'https://app.example.com/app/callback',
            'EMAIL_HOST': 'smtp.zoho.com',
            'EMAIL_HOST_USER': 'noreply@example.com',
            'EMAIL_HOST_PASSWORD': 'smtp-app-password',
            'DEFAULT_FROM_EMAIL': 'noreply@example.com',
            'MEDIA_ROOT': '/tmp/hr-media',
        }
        with self.settings(**{}):
            original = {key: os.environ.get(key) for key in env}
            try:
                os.environ.update(env)
                out = StringIO()
                call_command('validate_production', stdout=out)
                self.assertIn('PASS', out.getvalue())
            finally:
                for key, value in original.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    def test_validate_production_fails_for_missing_required_values(self):
        env = {
            'APP_ENV': 'production',
            'DEBUG': 'False',
            'SECRET_KEY': 'invalid-secret',
            'FIELD_ENCRYPTION_KEY': '',
            'DATABASE_URL': '',
            'ALLOWED_HOSTS': '',
            'CSRF_TRUSTED_ORIGINS': '',
        }
        original = {key: os.environ.get(key) for key in env}
        try:
            os.environ.update(env)
            with self.assertRaises(CommandError):
                call_command('validate_production', stdout=StringIO())
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_provision_employee_is_idempotent(self):
        employee = Employee.objects.create_user(
            username='existing-user',
            email='user@example.com',
            password='x',
            company=self.company,
            role=EmployeeRole.EMPLOYEE,
            is_active=True,
        )

        with self.assertRaises(CommandError):
            call_command(
                'provision_employee',
                '--email', employee.email,
                '--first-name', 'Existing',
                '--last-name', 'User',
                '--company', self.company.name,
                stdout=StringIO(),
            )
