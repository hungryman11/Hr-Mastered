from django.core.exceptions import ValidationError
from django.db import models

from .base import BaseModel


def default_working_weekdays():
    return [0, 1, 2, 3, 4]


class CompanyWorkCalendar(BaseModel):
    """One HR-managed work calendar per company.

    Weekdays use Python's convention: Monday is 0 and Sunday is 6.
    """

    company = models.OneToOneField(
        'core.Company', on_delete=models.CASCADE, related_name='work_calendar',
    )
    working_weekdays = models.JSONField(default=default_working_weekdays)
    include_nigerian_public_holidays = models.BooleanField(default=True)

    class Meta:
        db_table = 'company_work_calendars'

    def clean(self):
        days = self.working_weekdays
        if not isinstance(days, list) or not days:
            raise ValidationError({'working_weekdays': 'Select at least one working weekday.'})
        if any(not isinstance(day, int) or isinstance(day, bool) or day < 0 or day > 6 for day in days):
            raise ValidationError({'working_weekdays': 'Weekdays must be unique integers from 0 (Monday) to 6 (Sunday).'})
        if len(set(days)) != len(days):
            raise ValidationError({'working_weekdays': 'Weekdays must not contain duplicates.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
