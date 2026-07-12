from django.core.management.base import BaseCommand

from core.models import EmployeeRole


class Command(BaseCommand):
    help = 'Bootstrap default HR roles in the database.'

    def handle(self, *args, **options):
        self.stdout.write('Employee roles available:')
        for role in EmployeeRole.choices:
            self.stdout.write(f'- {role[0]}: {role[1]}')
