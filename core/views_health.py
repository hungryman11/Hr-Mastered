import logging
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from core.models import DeliveryJob

logger = logging.getLogger(__name__)


def health_check(request):
    """Health check endpoint for Render/k8s/Docker health checks."""
    db_ok = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
            db_ok = bool(row and row[0] == 1)
    except Exception as exc:
        logger.error("Health check DB query failed: %s", exc)

    oldest_pending = DeliveryJob.objects.filter(status=DeliveryJob.Status.PENDING).order_by('created_at').first()
    worker_lag_seconds = None
    if oldest_pending:
        worker_lag_seconds = int((timezone.now() - oldest_pending.created_at).total_seconds())

    status_code = 200 if db_ok else 503
    return JsonResponse({
        'status': 'healthy' if db_ok else 'unhealthy',
        'db': 'ok' if db_ok else 'error',
        'worker_lag_seconds': worker_lag_seconds,
        'timestamp': timezone.now().isoformat(),
    }, status=status_code)
