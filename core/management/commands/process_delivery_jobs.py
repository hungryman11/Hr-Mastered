from django.core.management.base import BaseCommand
from core.delivery import DeliveryService


class Command(BaseCommand):
    help = 'Process queued external delivery jobs.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50)

    def handle(self, *args, **options):
        processed = 0
        while processed < options['limit']:
            job = DeliveryService.claim_next()
            if not job:
                break
            DeliveryService.process(job)
            processed += 1
        self.stdout.write(self.style.SUCCESS(f'Processed {processed} delivery job(s).'))
