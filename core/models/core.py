import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone

from .base import BaseModel, CompanyScopedModel, SoftDeleteQuerySet


class Company(BaseModel):
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'companies'
        verbose_name_plural = 'companies'

    def __str__(self):
        return self.name


class Department(CompanyScopedModel):
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'departments'

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Position(CompanyScopedModel):
    title = models.CharField(max_length=150)
    code = models.CharField(max_length=50, blank=True)
    org_unit = models.ForeignKey('core.OrgUnit', null=True, blank=True, on_delete=models.SET_NULL, related_name='positions')
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'positions'

    def __str__(self):
        return f"{self.title} ({self.company.name})"


class EmployeeManager(UserManager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)


class EmployeeRole(models.TextChoices):
    FINANCE = 'FINANCE', 'Finance approver'
    ADMIN = 'ADMIN', 'Administrator'
    SUPERVISOR = 'SUPERVISOR', 'Supervisor'
    HOD = 'HOD', 'Head of Department'
    HR_ADMIN = 'HR_ADMIN', 'HR Admin'
    MANAGER = 'MANAGER', 'Manager'
    EMPLOYEE = 'EMPLOYEE', 'Employee'


class OnboardingStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    COMPLETE = 'COMPLETE', 'Complete'
    FAILED = 'FAILED', 'Failed'


class Employee(AbstractUser):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='employees',
    )
    department = models.ForeignKey(
        'Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
    )
    org_unit = models.ForeignKey(
        'core.OrgUnit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
    )
    position = models.ForeignKey(
        'core.Position',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
    )
    role = models.CharField(
        max_length=20,
        choices=EmployeeRole.choices,
        default=EmployeeRole.EMPLOYEE,
    )
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_reports',
    )
    is_org_admin = models.BooleanField(
        default=False,
        help_text=(
            'Grants permission to edit the organogram: org units, and other employees\' '
            'role/manager/org-unit assignments. Independent of role; grant deliberately '
            'to specific trusted people rather than to every HR Admin.'
        ),
    )
    onboarding_status = models.CharField(
        max_length=20,
        choices=OnboardingStatus.choices,
        default=OnboardingStatus.PENDING,
    )
    zoho_user_id = models.CharField(
        max_length=150,
        unique=True,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_employees',
    )
    updated_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_employees',
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='employee_groups',
        blank=True,
        help_text='The groups this employee belongs to.',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='employee_user_permissions',
        blank=True,
        help_text='Specific permissions for this employee.',
    )

    objects = EmployeeManager()
    all_objects = UserManager()

    class Meta:
        db_table = 'employees'

    def __str__(self):
        if self.company:
            return f"{self.get_full_name() or self.username} - {self.company.name}"
        return self.get_full_name() or self.username

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError

        # Validate cross-company boundaries
        if self.company_id:
            if self.department_id and self.department.company_id != self.company_id:
                raise ValidationError({'department': 'Department must belong to the same company.'})
            if self.org_unit_id and self.org_unit.company_id != self.company_id:
                raise ValidationError({'org_unit': 'Org unit must belong to the same company.'})
            if self.position_id and self.position.company_id != self.company_id:
                raise ValidationError({'position': 'Position must belong to the same company.'})
            if self.manager_id and self.manager.company_id != self.company_id:
                raise ValidationError({'manager': 'Manager must belong to the same company.'})

        # Validate Position / OrgUnit consistency:
        # If Employee.position exists AND Employee.position.org_unit exists,
        # Employee.org_unit must equal Employee.position.org_unit.
        if self.position_id and self.position.org_unit_id:
            if not self.org_unit_id or self.org_unit_id != self.position.org_unit_id:
                pos_unit_name = self.position.org_unit.name if self.position.org_unit else str(self.position.org_unit_id)
                raise ValidationError({
                    'org_unit': f'Position "{self.position.title}" belongs to org unit "{pos_unit_name}". Employee org unit must match.'
                })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at', 'updated_at'])

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
