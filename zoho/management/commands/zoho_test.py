from django.test import override_settings
from django.core.management.base import BaseCommand
from zoho.services import get_zoho_auth_headers, get_zoho_config


class Command(BaseCommand):
    help = "Print a Zoho auth header sample using either the real API or the local mock mode"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mock",
            action="store_true",
            help="Force the local mock mode even if no Zoho credentials are set",
        )

    def handle(self, *args, **options):
        from django.conf import settings

        use_mock = options["mock"] or getattr(settings, "ZOHO_USE_MOCK", False)
        with override_settings(ZOHO_USE_MOCK=use_mock):
            config = get_zoho_config()
            headers = get_zoho_auth_headers()

        self.stdout.write(self.style.SUCCESS("Zoho config summary:"))
        self.stdout.write(f"- mock mode: {use_mock}")
        self.stdout.write(f"- client_id: {config.get('client_id') or '(empty)'}")
        self.stdout.write(f"- org_id: {config.get('org_id') or '(empty)'}")
        self.stdout.write(self.style.SUCCESS("Sample auth headers:"))
        for key, value in headers.items():
            self.stdout.write(f"- {key}: {value}")
