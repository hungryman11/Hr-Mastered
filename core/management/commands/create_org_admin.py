import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Company, Employee, EmployeeRole


class Command(BaseCommand):
    help = 'Safely create or update the first organization administrator for a company.'

    def add_arguments(self, parser):
        parser.add_argument('--company', required=True, help='Existing company name to bootstrap.')
        parser.add_argument('--first-name', required=True, help='First name for the organization admin.')
        parser.add_argument('--last-name', required=True, help='Last name for the organization admin.')
        parser.add_argument('--username', required=True, help='Unique username for the organization admin.')
        parser.add_argument('--email', required=True, help='Unique work email for the organization admin.')
        parser.add_argument('--password', required=True, help='Strong password for the organization admin account.')

    def _validate_fields(self, username, email):
        if not username.strip():
            raise CommandError('Username is required.')
        if not email.strip():
            raise CommandError('Email is required.')
        if '@' not in email or '.' not in email.rsplit('@', 1)[-1]:
            raise CommandError('Email must be a valid address.')

    @staticmethod
    def _password_is_strong(password: str) -> bool:
        if len(password) < 12:
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'\d', password):
            return False
        if not re.search(r'[^A-Za-z0-9]', password):
            return False
        return True

    @transaction.atomic
    def handle(self, *args, **options):
        company_name = str(options['company']).strip()
        first_name = str(options['first_name']).strip()
        last_name = str(options['last_name']).strip()
        username = str(options['username']).strip()
        email = str(options['email']).strip().lower()
        password = str(options['password'])

        if not company_name:
            raise CommandError('Company name is required.')
        if not first_name or not last_name:
            raise CommandError('First name and last name are required.')

        self._validate_fields(username, email)

        if not self._password_is_strong(password):
            raise CommandError('Password must be at least 12 characters and include upper/lowercase letters, a number, and a symbol.')

        company = Company.objects.filter(name=company_name).first()
        if not company:
            raise CommandError(f'Company not found: {company_name}')

        existing_username = Employee.objects.filter(username__iexact=username).exclude(company__isnull=True).first()
        if existing_username and existing_username.company_id != company.id:
            raise CommandError('Username is already assigned to a different company.')

        existing_email = Employee.objects.filter(email__iexact=email).exclude(company__isnull=True).first()
        if existing_email and existing_email.company_id != company.id:
            raise CommandError('Email is already assigned to a different company.')

        admin = Employee.objects.filter(company=company, is_org_admin=True).first()
        if admin and not (existing_username and existing_username.pk == admin.pk) and not (existing_email and existing_email.pk == admin.pk):
            raise CommandError(
                'An organization administrator already exists for this company; update that account instead of creating a second one.'
            )

        employee = Employee.objects.filter(company=company, username__iexact=username).first() or Employee.objects.filter(company=company, email__iexact=email).first()
        if employee is None:
            employee = Employee.objects.create(
                company=company,
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=EmployeeRole.HR_ADMIN,
                is_org_admin=True,
                is_active=True,
                is_staff=False,
                is_superuser=False,
            )
        else:
            employee.company = company
            employee.first_name = first_name
            employee.last_name = last_name
            employee.username = username
            employee.email = email
            employee.role = EmployeeRole.HR_ADMIN
            employee.is_org_admin = True
            employee.is_active = True
            employee.is_staff = False
            employee.is_superuser = False
            employee.save()

        employee.set_password(password)
        employee.save(update_fields=['password', 'updated_at'])

        self.stdout.write(self.style.SUCCESS(
            f'Organization admin ready for company "{company.name}": {employee.username} ({employee.email})'
        ))
