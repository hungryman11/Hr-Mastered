import json
import logging
import signal
import sys
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.delivery import DeliveryService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Continuously process queued email and WorkDrive delivery jobs.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shutdown_requested = False

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=int, default=15, help='Seconds between polls (minimum 1).')
        parser.add_argument('--batch-size', type=int, default=50, help='Max jobs per batch.')
        parser.add_argument('--max-runtime', type=int, default=3600, help='Max runtime in seconds before exiting (0 = infinite).')

    def _handle_signal(self, signum, frame):
        self.stdout.write(self.style.WARNING(f'Received signal {signum}. Draining current batch and shutting down...'))
        self.shutdown_requested = True

    def handle(self, *args, **options):
        interval = max(1, options['interval'])
        max_runtime = options['max_runtime']
        start_time = time.time()

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        self.stdout.write(self.style.SUCCESS(f'Delivery worker started; polling every {interval}s (max runtime: {max_runtime}s).'))

        try:
            while not self.shutdown_requested:
                if max_runtime > 0 and (time.time() - start_time) >= max_runtime:
                    self.stdout.write(self.style.SUCCESS('Max runtime reached. Worker exiting for planned restart.'))
                    break

                processed = 0
                while processed < options['batch_size'] and not self.shutdown_requested:
                    job = DeliveryService.claim_next()
                    if not job:
                        break
                    
                    t0 = time.time()
                    res_job = DeliveryService.process(job)
                    duration_ms = round((time.time() - t0) * 1000, 2)
                    
                    log_data = {
                        'event': 'delivery_job_processed',
                        'job_uuid': str(res_job.uuid),
                        'kind': res_job.kind,
                        'status': res_job.status,
                        'attempts': res_job.attempts,
                        'duration_ms': duration_ms,
                        'timestamp': timezone.now().isoformat(),
                    }
                    self.stdout.write(json.dumps(log_data))
                    processed += 1

                time.sleep(interval)
        except Exception as exc:
            logger.exception("Delivery worker crashed unexpectedly: %s", exc)
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS('Delivery worker stopped cleanly.'))
