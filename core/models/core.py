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


class EmployeeManager(UserManager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)


class EmployeeRole(models.TextChoices):
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
    onboarding_status = models.CharField(
        max_length=20,
        choices=OnboardingStatus.choices,
        default=OnboardingStatus.PENDING,
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

    def delete(self, *args, **kwargs):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at', 'updated_at'])

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
