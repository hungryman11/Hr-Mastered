from django.urls import include, path
from rest_framework.routers import DefaultRouter

from zoho.api.views import EmailLogViewSet, EmployeeDocumentViewSet, WorkDriveFolderViewSet

from zoho.views import zoho_login_url_api_view, zoho_oauth_login_callback_api_view

router = DefaultRouter()
router.register(r'documents', EmployeeDocumentViewSet, basename='document')
router.register(r'folders', WorkDriveFolderViewSet, basename='folder')
router.register(r'email-logs', EmailLogViewSet, basename='email-log')

urlpatterns = [
    path('zoho/auth/login-url/', zoho_login_url_api_view, name='zoho-auth-login-url'),
    path('zoho/auth/callback/', zoho_oauth_login_callback_api_view, name='zoho-auth-callback'),
    path('', include(router.urls)),
]
