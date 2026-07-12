from django.urls import include, path
from rest_framework.routers import DefaultRouter

from zoho.api.views import EmailLogViewSet, EmployeeDocumentViewSet, WorkDriveFolderViewSet

router = DefaultRouter()
router.register(r'documents', EmployeeDocumentViewSet, basename='document')
router.register(r'folders', WorkDriveFolderViewSet, basename='folder')
router.register(r'email-logs', EmailLogViewSet, basename='email-log')

urlpatterns = [
    path('', include(router.urls)),
]
