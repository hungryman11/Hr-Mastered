from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Company, Department, Employee, EmployeeRole, LeaveType, OrgUnit


class Command(BaseCommand):
    help = 'Seed a small demo dataset for the HR SaaS platform.'

    def add_arguments(self, parser):
        parser.add_argument('--company', default='Globex Corp', help='Demo company name')
        parser.add_argument('--admin-email', default='hr@globex.com', help='HR admin email')
        parser.add_argument('--admin-password', default='ChangeMe123!', help='HR admin password')

    @transaction.atomic
    def handle(self, *args, **options):
        company, _ = Company.objects.get_or_create(name=options['company'])
        department, _ = Department.objects.get_or_create(company=company, name='People Ops')
        board, _ = OrgUnit.objects.get_or_create(company=company, name='Board of Directors', unit_type=OrgUnit.UnitType.BOARD)
        exec_unit, _ = OrgUnit.objects.get_or_create(company=company, name='Executive Office', unit_type=OrgUnit.UnitType.EXECUTIVE, parent=board)
        people_ops, _ = OrgUnit.objects.get_or_create(company=company, name='People Operations', unit_type=OrgUnit.UnitType.DEPARTMENT, parent=exec_unit)
        leave_type, _ = LeaveType.objects.get_or_create(
            company=company,
            name='Paid Time Off',
            defaults={'default_days': 15},
        )

        admin_user, admin_created = Employee.objects.get_or_create(
            username='hradmin',
            defaults={
                'email': options['admin_email'],
                'company': company,
                'department': department,
                'org_unit': people_ops,
                'role': EmployeeRole.HR_ADMIN,
                'is_staff': True,
                'is_superuser': False,
            },
        )
        if admin_created:
            admin_user.set_password(options['admin_password'])
            admin_user.first_name = 'HR'
            admin_user.last_name = 'Admin'
            admin_user.save()

        exec_unit.head = admin_user
        exec_unit.save(update_fields=['head', 'updated_at'])

        manager, manager_created = Employee.objects.get_or_create(
            username='manager1',
            defaults={
                'email': 'manager@globex.com',
                'company': company,
                'department': department,
                'org_unit': people_ops,
                'role': EmployeeRole.MANAGER,
                'manager': admin_user,
                'is_staff': False,
                'is_superuser': False,
            },
        )
        if manager_created:
            manager.set_password('ChangeMe123!')
            manager.first_name = 'Megan'
            manager.last_name = 'Manager'
            manager.save()

        employee, employee_created = Employee.objects.get_or_create(
            username='employee1',
            defaults={
                'email': 'employee@globex.com',
                'company': company,
                'department': department,
                'org_unit': people_ops,
                'role': EmployeeRole.EMPLOYEE,
                'manager': manager,
                'is_staff': False,
                'is_superuser': False,
            },
        )
        if employee_created:
            employee.set_password('ChangeMe123!')
            employee.first_name = 'Eddie'
            employee.last_name = 'Employee'
            employee.save()

        self.stdout.write(self.style.SUCCESS('Seeded demo SaaS data:'))
        self.stdout.write(f'- Company: {company.name}')
        self.stdout.write(f'- Org root: {board.name}')
        self.stdout.write(f'- Department: {department.name}')
        self.stdout.write(f'- Leave type: {leave_type.name}')
        self.stdout.write(f'- HR admin: {admin_user.username} / {options["admin_password"]}')
        self.stdout.write(f'- Manager: {manager.username} / ChangeMe123!')
        self.stdout.write(f'- Employee: {employee.username} / ChangeMe123!')
