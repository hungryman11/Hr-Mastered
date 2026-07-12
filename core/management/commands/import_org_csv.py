from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from core.models import Company, Department, Employee, EmployeeRole, OrgUnit


class Command(BaseCommand):
    help = 'Import employees and reporting lines from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', help='Path to CSV file')
        parser.add_argument('--company', required=True, help='Company name')
        parser.add_argument('--dry-run', action='store_true', help='Validate without saving')

    def _resolve_org_unit(self, company, path):
        parts = [p.strip() for p in (path or '').split('>') if p.strip()]
        parent = None
        unit = None
        for index, name in enumerate(parts):
            unit_type = OrgUnit.UnitType.DEPARTMENT if index == len(parts) - 1 else OrgUnit.UnitType.DIVISION
            unit, _ = OrgUnit.objects.get_or_create(company=company, parent=parent, name=name, defaults={'unit_type': unit_type})
            if unit.unit_type != unit_type:
                unit.unit_type = unit_type
                unit.save(update_fields=['unit_type', 'updated_at'])
            parent = unit
        return unit

    def _role_from_value(self, value):
        value = (value or '').strip().upper()
        return value if value in {choice[0] for choice in EmployeeRole.choices} else EmployeeRole.EMPLOYEE

    @transaction.atomic
    def handle(self, *args, **options):
        import csv
        from pathlib import Path

        company = Company.objects.get(name=options['company'])
        csv_path = Path(options['csv_path'])
        created = 0
        updated = 0

        with csv_path.open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                email = (row.get('email') or '').strip().lower()
                if not email:
                    continue

                full_name = (row.get('full_name') or '').strip()
                first_name, _, last_name = full_name.partition(' ')
                manager_email = (row.get('manager_email') or '').strip().lower() or None
                org_path = row.get('org_path') or row.get('org_unit') or ''
                department_name = (row.get('department') or '').strip() or 'People Ops'
                username = row.get('username') or slugify(email.split('@')[0]).replace('-', '')

                department, _ = Department.objects.get_or_create(company=company, name=department_name)
                org_unit = self._resolve_org_unit(company, org_path) if org_path else None
                manager = Employee.objects.filter(company=company, email=manager_email).first() if manager_email else None
                role = self._role_from_value(row.get('role'))

                employee, is_created = Employee.objects.get_or_create(
                    company=company,
                    email=email,
                    defaults={
                        'username': username,
                        'first_name': first_name,
                        'last_name': last_name,
                        'department': department,
                        'org_unit': org_unit,
                        'manager': manager,
                        'role': role,
                    },
                )
                employee.username = employee.username or username
                employee.first_name = first_name or employee.first_name
                employee.last_name = last_name or employee.last_name
                employee.department = department
                employee.org_unit = org_unit
                employee.manager = manager
                employee.role = role
                employee.save()
                created += int(is_created)
                updated += int(not is_created)

        self.stdout.write(self.style.SUCCESS(f'Imported employees for {company.name}: created={created}, updated={updated}'))
