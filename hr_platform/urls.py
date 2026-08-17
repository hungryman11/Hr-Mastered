from django.contrib import admin
from django.urls import include, path, re_path

from zoho.views import home_view, zoho_demo_view, zoho_oauth_callback_view
from core.views_health import health_check
from core.portal_views import PortalIndexView

urlpatterns = [
    path('', home_view, name='home'),
    path('admin/', admin.site.urls),
    path('zoho-demo/', zoho_demo_view, name='zoho-demo'),
    path('zoho/oauth/callback/', zoho_oauth_callback_view, name='zoho-oauth-callback'),
    path('api/', include('core.urls')),
    path('api/', include('zoho.urls')),
    path('healthz/', health_check, name='health-check'),
    path('app/', PortalIndexView.as_view(), name='portal-index'),
    re_path(r'^app/.*$', PortalIndexView.as_view(), name='portal-catchall'),
]
