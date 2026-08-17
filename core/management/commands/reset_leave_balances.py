from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from core.models import Employee, LeaveBalance, LeaveType


class Command(BaseCommand):
    help = 'Year-end cron task: rolls over balances for the new calendar year and applies carry-over rules.'

    def add_arguments(self, parser):
        parser.add_argument('--target-year', type=int, default=None, help='Target year to generate balances for (defaults to current calendar year).')

    def handle(self, *args, **options):
        current_year = timezone.now().year
        target_year = options['target_year'] or current_year
        previous_year = target_year - 1

        self.stdout.write(self.style.NOTICE(f"Processing leave balance carry-overs from {previous_year} to {target_year}..."))

        employees = Employee.objects.select_related('company').filter(is_active=True)
        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for employee in employees:
                leave_types = LeaveType.objects.filter(company=employee.company)
                for lt in leave_types:
                    prev_bal = LeaveBalance.objects.filter(employee=employee, leave_type=lt, year=previous_year).first()
                    carry_over = 0
                    if prev_bal:
                        remaining = max(0, float(prev_bal.remaining_days))
                        max_carry = float(lt.carry_over_days or 0)
                        carry_over = min(remaining, max_carry)

                    bal, created = LeaveBalance.objects.get_or_create(
                        employee=employee,
                        leave_type=lt,
                        year=target_year,
                        defaults={
                            'company': employee.company,
                            'allocated_days': lt.default_days,
                            'carried_over_days': carry_over,
                            'used_days': 0,
                        }
                    )
                    if created:
                        created_count += 1
                    else:
                        bal.carried_over_days = carry_over
                        bal.save(update_fields=['carried_over_days', 'updated_at'])
                        updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Leave balances updated for year {target_year}: {created_count} created, {updated_count} updated."))
