from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from .base import CompanyScopedModel


class SalaryRecord(CompanyScopedModel):
    """
    Structured salary record capturing base pay and all statutory allowances
    with effective-date history and overlap prevention.
    """

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        SUPERSEDED = 'SUPERSEDED', 'Superseded'
        ARCHIVED = 'ARCHIVED', 'Archived'

    class Currency(models.TextChoices):
        NGN = 'NGN', 'Nigerian Naira'
        USD = 'USD', 'US Dollar'
        GBP = 'GBP', 'British Pound'
        EUR = 'EUR', 'Euro'

    employee = models.ForeignKey(
        'core.Employee', on_delete=models.CASCADE, related_name='salary_records'
    )

    # Effective date range — end_date NULL means currently active record
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    currency = models.CharField(
        max_length=3, choices=Currency.choices, default=Currency.NGN
    )

    # Salary components
    base_salary = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    housing_allowance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    transport_allowance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    meal_allowance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    other_allowances = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    # Notes / audit trail
    reason = models.TextField(blank=True, help_text='Reason for salary change (e.g. promotion, annual review)')

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        db_table = 'salary_records'
        ordering = ['-effective_date']

    def __str__(self):
        return f'{self.employee} – {self.currency} {self.gross_salary} (from {self.effective_date})'

    @property
    def gross_salary(self) -> Decimal:
        return (
            self.base_salary
            + self.housing_allowance
            + self.transport_allowance
            + self.meal_allowance
            + self.other_allowances
        )

    def clean(self):
        super().clean()

        # Employee must belong to same company
        if self.employee_id and self.employee.company_id != self.company_id:
            raise ValidationError('Employee must belong to the same company.')

        # end_date must come after effective_date
        if self.end_date and self.end_date <= self.effective_date:
            raise ValidationError(
                {'end_date': 'End date must be strictly after the effective date.'}
            )

        # Prevent overlapping ACTIVE salary records for the same employee
        if self.status == self.Status.ACTIVE:
            overlap_qs = SalaryRecord.objects.filter(
                company=self.company,
                employee=self.employee,
                status=self.Status.ACTIVE,
            ).exclude(pk=self.pk)

            for other in overlap_qs:
                self_start = self.effective_date
                self_end = self.end_date  # None = open-ended

                other_start = other.effective_date
                other_end = other.end_date

                # Two date ranges [A, B] and [C, D] overlap if A <= D and C <= B
                # Treat None (open-ended) as infinite future
                if (self_end is None or other_start <= self_end) and \
                   (other_end is None or self_start <= other_end):
                    raise ValidationError(
                        f'An active salary record already exists for this employee '
                        f'that overlaps with [{self.effective_date} – {self.end_date or "present"}]. '
                        f'Please supersede or archive the existing record before creating a new one.'
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
