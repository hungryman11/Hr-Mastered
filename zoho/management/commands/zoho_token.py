from django.core.management.base import BaseCommand
from zoho.services import ZohoWorkDriveService

class Command(BaseCommand):
    help = "Prints a fresh Zoho OAuth access token"

    def handle(self, *args, **options):
        service = ZohoWorkDriveService()
        token = service._refresh_access_token()
        self.stdout.write(f"Zoho access token: {token}")
