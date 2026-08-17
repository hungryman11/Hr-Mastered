from django.db import models
from .base import CompanyScopedModel
import uuid
from django.core.exceptions import ValidationError
from decimal import Decimal


class KpiCategory(CompanyScopedModel):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'kpi_categories'

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class KpiTemplate(CompanyScopedModel):
    class MeasurementType(models.TextChoices):
        NUMERIC = 'NUMERIC', 'Numeric'
        PERCENT = 'PERCENT', 'Percentage'
        RATING = 'RATING', 'Rating'
        BOOLEAN = 'BOOLEAN', 'Boolean'
        TIME = 'TIME', 'Time'

    class Direction(models.TextChoices):
        HIGHER_IS_BETTER = 'HIGHER', 'Higher is better'
        LOWER_IS_BETTER = 'LOWER', 'Lower is better'
        TARGET_BASED = 'TARGET', 'Target based'

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey('core.KpiCategory', null=True, blank=True, on_delete=models.SET_NULL, related_name='templates')
    measurement_type = models.CharField(max_length=20, choices=MeasurementType.choices, default=MeasurementType.NUMERIC)
    direction = models.CharField(max_length=20, choices=Direction.choices, default=Direction.HIGHER_IS_BETTER)
    default_target = models.CharField(max_length=100, blank=True)
    default_weight = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    frequency = models.CharField(max_length=50, blank=True)
    data_source = models.CharField(max_length=255, blank=True)
    scoring_method = models.CharField(max_length=100, blank=True)
    min_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'kpi_templates'

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class KpiFramework(CompanyScopedModel):
    class ScopeType(models.TextChoices):
        GLOBAL = 'GLOBAL', 'Global'
        DEPARTMENT = 'DEPARTMENT', 'Department'
        POSITION = 'POSITION', 'Position'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PUBLISHED = 'PUBLISHED', 'Published'
        ARCHIVED = 'ARCHIVED', 'Archived'

    name = models.CharField(max_length=200)
    scope_type = models.CharField(max_length=20, choices=ScopeType.choices, default=ScopeType.DEPARTMENT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    org_unit = models.ForeignKey('core.OrgUnit', null=True, blank=True, on_delete=models.SET_NULL)
    position = models.ForeignKey('core.Position', null=True, blank=True, on_delete=models.SET_NULL, related_name='frameworks')

    class Meta:
        db_table = 'kpi_frameworks'

    def __str__(self):
        return f"{self.name} ({self.company.name})"

    def validate_publishing(self):
        """Validate framework completeness before publishing (items must sum to 100)."""
        from decimal import Decimal
        total = sum((Decimal(str(item.weight or 0)) for item in self.items.all()), Decimal('0'))
        if abs(total - Decimal('100')) > Decimal('0.01'):
            raise ValidationError(f'Framework total weights must sum to 100 (±0.01) before publishing. Current total is {total}.')


class KpiFrameworkItem(models.Model):
    framework = models.ForeignKey('core.KpiFramework', related_name='items', on_delete=models.CASCADE)
    template = models.ForeignKey('core.KpiTemplate', on_delete=models.CASCADE)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    target = models.CharField(max_length=100, blank=True)
    scoring_method_override = models.CharField(max_length=100, blank=True)
    direction_override = models.CharField(max_length=20, blank=True)
    sequence = models.IntegerField(default=0)
    required = models.BooleanField(default=False)

    class Meta:
        db_table = 'kpi_framework_items'
        unique_together = ('framework', 'template')

    def __str__(self):
        return f"{self.framework.name} - {self.template.name}"


class EmployeeKpiOverride(CompanyScopedModel):
    class ActionType(models.TextChoices):
        ADD = 'ADD', 'Add'
        MODIFY = 'MODIFY', 'Modify'
        REMOVE = 'REMOVE', 'Remove'

    employee = models.ForeignKey('core.Employee', on_delete=models.CASCADE, related_name='kpi_overrides')
    template = models.ForeignKey('core.KpiTemplate', on_delete=models.CASCADE)
    action_type = models.CharField(max_length=10, choices=ActionType.choices, default=ActionType.MODIFY)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    target = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'employee_kpi_overrides'

    def __str__(self):
        return f"Override [{self.action_type}] {self.employee} - {self.template.name}"

    def clean(self):
        # Ensure override belongs to same company as employee and template
        if self.employee.company_id != self.company_id or self.template.company_id != self.company_id:
            raise ValidationError('Employee, template and override must belong to the same company.')
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError({'effective_to': 'Effective end date cannot be before start date.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PerformanceCycle(CompanyScopedModel):
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    review_deadline = models.DateField(null=True, blank=True)
    locked = models.BooleanField(default=False)

    class Meta:
        db_table = 'performance_cycles'

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class EmployeeKpiAssignment(CompanyScopedModel):
    # Snapshot of a KPI assignment for a specific cycle and employee
    cycle = models.ForeignKey('core.PerformanceCycle', on_delete=models.CASCADE, related_name='assignments')
    employee = models.ForeignKey('core.Employee', on_delete=models.CASCADE, related_name='kpi_assignments')
    template = models.ForeignKey('core.KpiTemplate', on_delete=models.CASCADE)
    # Snapshot of template fields at time of assignment creation
    template_name = models.CharField(max_length=200, blank=True)
    measurement_type = models.CharField(max_length=20, blank=True)
    direction = models.CharField(max_length=20, blank=True)
    scoring_method = models.CharField(max_length=100, blank=True)
    category_name = models.CharField(max_length=200, blank=True)
    template_description = models.TextField(blank=True)
    template_default_target = models.CharField(max_length=100, blank=True)
    template_default_weight = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    template_frequency = models.CharField(max_length=50, blank=True)
    template_data_source = models.CharField(max_length=255, blank=True)
    # Full template snapshot for easy reference and future changes
    full_template_snapshot = models.JSONField(default=dict, blank=True)
    target = models.CharField(max_length=100, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    source = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'employee_kpi_assignments'

    def __str__(self):
        return f"{self.employee} - {self.template.name} ({self.cycle.name})"


class KpiMeasurement(CompanyScopedModel):
    assignment = models.ForeignKey('core.EmployeeKpiAssignment', on_delete=models.CASCADE, related_name='measurements')
    measured_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL)
    value = models.CharField(max_length=200)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'kpi_measurements'

    def __str__(self):
        return f"{self.assignment} @ {self.measured_at} = {self.value}"


class PerformanceReview(CompanyScopedModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted for Review'
        MANAGER_REVIEWED = 'MANAGER_REVIEWED', 'Manager Reviewed'
        HR_REVIEWED = 'HR_REVIEWED', 'HR Reviewed'
        CALIBRATED = 'CALIBRATED', 'Calibrated'
        FINALIZED = 'FINALIZED', 'Finalized'

    cycle = models.ForeignKey('core.PerformanceCycle', on_delete=models.CASCADE, related_name='reviews')
    employee = models.ForeignKey('core.Employee', on_delete=models.CASCADE, related_name='performance_reviews')
    reviewer = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='reviews_conducted')

    system_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    employee_self_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    employee_comments = models.TextField(blank=True)

    manager_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    manager_comments = models.TextField(blank=True)

    hr_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hr_comments = models.TextField(blank=True)

    calibrated_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    calibrated_by = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='calibrated_reviews')
    calibrated_at = models.DateTimeField(null=True, blank=True)

    final_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    final_comments = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    finalized_by = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='finalized_reviews')
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'performance_reviews'
        unique_together = ('company', 'cycle', 'employee')

    def __str__(self):
        return f"Review: {self.employee} - {self.cycle.name} [{self.status}]"

    def clean(self):
        super().clean()
        if self.employee and self.employee.company_id != self.company_id:
            raise ValidationError('Employee must belong to the same company.')
        if self.cycle and self.cycle.company_id != self.company_id:
            raise ValidationError('Performance cycle must belong to the same company.')

    def save(self, *args, **kwargs):
        if self.pk:
            old = PerformanceReview.objects.filter(pk=self.pk).values('status').first()
            if old and old['status'] == self.Status.FINALIZED:
                raise ValidationError("Finalized performance reviews cannot be modified or deleted.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status == self.Status.FINALIZED:
            raise ValidationError("Finalized performance reviews cannot be modified or deleted.")
        return super().delete(*args, **kwargs)

