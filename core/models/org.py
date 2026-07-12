from django.db import models

from .base import CompanyScopedModel


class OrgUnit(CompanyScopedModel):
    class UnitType(models.TextChoices):
        BOARD = 'BOARD', 'Board'
        EXECUTIVE = 'EXECUTIVE', 'Executive'
        DIVISION = 'DIVISION', 'Division'
        DEPARTMENT = 'DEPARTMENT', 'Department'
        TEAM = 'TEAM', 'Team'
        FUNCTION = 'FUNCTION', 'Function'

    name = models.CharField(max_length=255)
    unit_type = models.CharField(max_length=20, choices=UnitType.choices)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
    )
    head = models.ForeignKey(
        'core.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_org_units',
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'org_units'
        unique_together = ('company', 'parent', 'name')
        ordering = ('sort_order', 'name')

    def __str__(self):
        return f'{self.name} ({self.company.name})'
