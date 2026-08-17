"""Create an isolated, repeatable UAT dataset without external integrations."""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    Company, Department, Employee, EmployeeKpiAssignment,
    EmployeeRole, KpiCategory, KpiFramework, KpiFrameworkItem, KpiMeasurement,
    KpiTemplate, LeaveApprovalPolicy, LeaveApprovalStep, LeaveBalance, LeaveRequest,
    LeaveType, OrgUnit, PerformanceCycle, PerformanceReview, Position, SalaryRecord,
)
from core.onboarding import ApprovalRoutingService


DEMO_COMPANY = 'Infinity Microfinance Bank — DEMO'
DEMO_PASSWORD = 'DemoPass123!'


class Command(BaseCommand):
    help = 'Seed the isolated Infinity Microfinance Bank UAT demonstration dataset.'

    @transaction.atomic
    def handle(self, *args, **options):
        company, _ = Company.objects.get_or_create(name=DEMO_COMPANY)
        departments = {
            name: Department.objects.get_or_create(company=company, name=name)[0]
            for name in ('Human Resources', 'Information Technology', 'Operations', 'Finance')
        }
        root, _ = OrgUnit.objects.get_or_create(
            company=company, parent=None, name='Infinity DEMO',
            defaults={'unit_type': OrgUnit.UnitType.EXECUTIVE},
        )
        units = {}
        for name in departments:
            units[name], _ = OrgUnit.objects.get_or_create(
                company=company, parent=root, name=name,
                defaults={'unit_type': OrgUnit.UnitType.DEPARTMENT},
            )

        positions = {}
        position_specs = {
            'HR Administrator': 'Human Resources', 'Software Engineer': 'Information Technology',
            'IT Manager': 'Information Technology', 'Head of Operations': 'Operations',
            'Operations Officer': 'Operations', 'Finance Officer': 'Finance',
            'Supervisor': 'Operations', 'Administrative Officer': 'Human Resources',
        }
        for title, unit_name in position_specs.items():
            positions[title], _ = Position.objects.get_or_create(
                company=company, title=title, org_unit=units[unit_name],
                defaults={'code': title.upper().replace(' ', '_')[:50], 'active': True},
            )

        people = {
            'demo.hr.admin': ('Demo', 'HR Admin', 'Human Resources', 'HR Administrator', EmployeeRole.HR_ADMIN, None, True),
            'demo.manager': ('Demo', 'Manager', 'Information Technology', 'IT Manager', EmployeeRole.MANAGER, 'demo.hr.admin', False),
            'demo.hod': ('Demo', 'HOD', 'Operations', 'Head of Operations', EmployeeRole.HOD, 'demo.hr.admin', False),
            'demo.employee': ('Demo', 'Employee', 'Information Technology', 'Software Engineer', EmployeeRole.EMPLOYEE, 'demo.manager', False),
            'demo.employee2': ('Demo', 'Operations Employee', 'Operations', 'Operations Officer', EmployeeRole.EMPLOYEE, 'demo.hod', False),
            'demo.finance': ('Demo', 'Finance', 'Finance', 'Finance Officer', EmployeeRole.FINANCE, 'demo.hr.admin', False),
            'demo.supervisor': ('Demo', 'Supervisor', 'Operations', 'Supervisor', EmployeeRole.SUPERVISOR, 'demo.hod', False),
            'demo.admin': ('Demo', 'Administrator', 'Human Resources', 'Administrative Officer', EmployeeRole.ADMIN, 'demo.hr.admin', False),
        }
        users = {}
        for username, (first, last, dept, position, role, manager_username, is_org_admin) in people.items():
            user, created = Employee.objects.get_or_create(username=username, defaults={'email': f'{username}@infinity-demo.local'})
            user.email = f'{username}@infinity-demo.local'
            user.first_name, user.last_name = first, last
            user.company, user.department, user.org_unit = company, departments[dept], units[dept]
            user.position, user.role = positions[position], role
            user.manager = users.get(manager_username)
            user.is_org_admin, user.is_active, user.is_staff, user.is_superuser = is_org_admin, True, False, False
            user.zoho_user_id = None
            if created:
                user.set_password(DEMO_PASSWORD)
            user.save()
            users[username] = user

        root.head = users['demo.hr.admin']
        root.save(update_fields=['head', 'updated_at'])
        for unit_name, username in {'Human Resources': 'demo.hr.admin', 'Information Technology': 'demo.manager', 'Operations': 'demo.hod', 'Finance': 'demo.finance'}.items():
            unit = units[unit_name]
            unit.head = users[username]
            unit.save(update_fields=['head', 'updated_at'])

        for unit_name, approver in {'Information Technology': users['demo.manager'], 'Operations': users['demo.hod']}.items():
            LeaveApprovalPolicy.objects.update_or_create(
                company=company, org_unit=units[unit_name],
                defaults={'first_approver_type': LeaveApprovalPolicy.ApproverType.SPECIFIC, 'first_approver_employee': approver,
                          'final_approver_type': LeaveApprovalPolicy.ApproverType.SPECIFIC,
                          'final_approver_employee': users['demo.hr.admin']},
            )

        annual_leave, _ = LeaveType.objects.get_or_create(
            company=company, name='Annual Leave',
            defaults={'default_days': 20, 'max_days_per_request': 10, 'carry_over_days': 5},
        )
        for user in users.values():
            LeaveBalance.objects.update_or_create(
                company=company, employee=user, leave_type=annual_leave, year=2026,
                defaults={'allocated_days': Decimal('20.00'), 'carried_over_days': Decimal('0.00'), 'used_days': Decimal('0.00')},
            )
        leave, _ = LeaveRequest.objects.get_or_create(
            company=company, employee=users['demo.employee'], leave_type=annual_leave,
            start_date=date(2026, 9, 14), end_date=date(2026, 9, 16),
            defaults={'days_requested': Decimal('3.00'), 'reason': 'UAT demonstration request',
                      'status': LeaveRequest.Status.PENDING_DEPARTMENT_HEAD,
                      'contact_during_leave': 'Demo contact', 'emergency_contact_name': 'Demo contact',
                      'emergency_contact_phone': '0000000000', 'handover_contact': 'Demo Manager',
                      'handover_notes': 'Demo handover notes', 'created_by': users['demo.employee'], 'updated_by': users['demo.employee']},
        )
        if not leave.approval_steps.exists():
            ApprovalRoutingService.create_steps(leave)

        category, _ = KpiCategory.objects.get_or_create(company=company, name='Software Delivery')
        template_specs = (
            ('Sprint Delivery', 'PERCENT', 'HIGHER', '90', '40.00', 'Monthly'),
            ('Production Quality', 'PERCENT', 'HIGHER', '95', '35.00', 'Monthly'),
            ('Knowledge Sharing', 'NUMERIC', 'HIGHER', '2', '25.00', 'Monthly'),
        )
        templates = []
        for name, measurement_type, direction, target, weight, frequency in template_specs:
            template, _ = KpiTemplate.objects.get_or_create(
                company=company, name=name,
                defaults={'category': category, 'measurement_type': measurement_type, 'direction': direction,
                          'default_target': target, 'default_weight': Decimal(weight), 'frequency': frequency,
                          'scoring_method': 'Standard UAT score', 'active': True},
            )
            templates.append(template)
        framework, _ = KpiFramework.objects.get_or_create(
            company=company, name='Demo Software Engineer KPI Framework',
            defaults={'scope_type': KpiFramework.ScopeType.POSITION, 'position': positions['Software Engineer'],
                      'status': KpiFramework.Status.DRAFT},
        )
        for sequence, (template, spec) in enumerate(zip(templates, template_specs), start=1):
            KpiFrameworkItem.objects.update_or_create(framework=framework, template=template,
                defaults={'weight': Decimal(spec[4]), 'target': spec[3], 'sequence': sequence, 'required': True})
        framework.status = KpiFramework.Status.PUBLISHED
        framework.validate_publishing()
        framework.save(update_fields=['status', 'updated_at'])
        cycle, _ = PerformanceCycle.objects.get_or_create(
            company=company, name='2026 UAT Performance Cycle',
            defaults={'start_date': date(2026, 1, 1), 'end_date': date(2026, 12, 31), 'review_deadline': date(2026, 12, 15)},
        )
        for template, spec in zip(templates, template_specs):
            assignment, _ = EmployeeKpiAssignment.objects.get_or_create(
                company=company, cycle=cycle, employee=users['demo.employee'], template=template,
                defaults={'template_name': template.name, 'measurement_type': template.measurement_type,
                          'direction': template.direction, 'scoring_method': template.scoring_method,
                          'category_name': category.name, 'template_description': template.description,
                          'template_default_target': template.default_target, 'template_default_weight': template.default_weight,
                          'template_frequency': template.frequency, 'template_data_source': template.data_source,
                          'full_template_snapshot': {'name': template.name, 'target': spec[3], 'weight': spec[4]},
                          'target': spec[3], 'weight': Decimal(spec[4]), 'source': {'framework': framework.name}},
            )
            if not assignment.measurements.exists():
                KpiMeasurement.objects.create(company=company, assignment=assignment, recorded_by=users['demo.manager'], value=spec[3], notes='Seeded UAT measurement')
        PerformanceReview.objects.update_or_create(
            company=company, cycle=cycle, employee=users['demo.employee'],
            defaults={'reviewer': users['demo.manager'], 'system_score': Decimal('91.00'), 'employee_self_score': Decimal('90.00'),
                      'employee_comments': 'Seeded UAT self-review.', 'status': PerformanceReview.Status.SUBMITTED},
        )
        salary, _ = SalaryRecord.objects.get_or_create(
            company=company, employee=users['demo.employee'], effective_date=date(2026, 1, 1),
            defaults={'currency': SalaryRecord.Currency.NGN, 'base_salary': Decimal('450000.00'),
                      'housing_allowance': Decimal('100000.00'), 'transport_allowance': Decimal('50000.00'),
                      'meal_allowance': Decimal('25000.00'), 'other_allowances': Decimal('0.00'),
                      'reason': 'UAT demonstration salary', 'status': SalaryRecord.Status.ACTIVE},
        )
        self.stdout.write(self.style.SUCCESS(f'Seeded {company.name} (idempotent).'))
        self.stdout.write(f'Demo password for all local demo users: {DEMO_PASSWORD}')
        self.stdout.write('Users: ' + ', '.join(users))
