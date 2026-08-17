from django.db import models

from .base import CompanyScopedModel


class CompanyHoliday(CompanyScopedModel):
    """A public or company closure day excluded from leave calculations."""

    name = models.CharField(max_length=150)
    date = models.DateField()
    is_national = models.BooleanField(default=False)

    class Meta:
        db_table = 'company_holidays'
        constraints = [
            models.UniqueConstraint(fields=('company', 'date'), name='unique_company_holiday_date'),
        ]
        ordering = ('date',)

    def __str__(self):
        return f'{self.name} ({self.date})'
