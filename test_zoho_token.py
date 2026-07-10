import os
import django
from dotenv import load_dotenv
# Ensure Django settings are configured before importing any models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_platform.settings')
# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
# Setup Django
django.setup()
from zoho.services import ZohoWorkDriveService
svc = ZohoWorkDriveService()
print('Access token:', svc._refresh_access_token())
