from django.core.exceptions import ValidationError
from django.db import models

from core.security import SensitiveValueCipher

from .base import BaseModel


class PayrollScopedModel(BaseModel):
    """Payroll tables intentionally use isolated reverse relations."""
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE)
    created_by = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    updated_by = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        abstract = True


class PayrollProfile(PayrollScopedModel):
    class EmploymentStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        TERMINATED = 'TERMINATED', 'Terminated'

    employee = models.OneToOneField('core.Employee', on_delete=models.CASCADE, related_name='payroll_profile')
    employee_number = models.CharField(max_length=50)
    base_salary = models.DecimalField(max_digits=14, decimal_places=2)
    bank_account_ciphertext = models.TextField(blank=True)
    bank_code = models.CharField(max_length=10, blank=True)
    pension_id_ciphertext = models.TextField(blank=True)
    tax_id_ciphertext = models.TextField(blank=True)
    employment_status = models.CharField(max_length=20, default=EmploymentStatus.ACTIVE)
    hire_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)
    data_processing_consented_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payroll_profiles'
        constraints = [models.UniqueConstraint(fields=('company', 'employee_number'), name='unique_payroll_employee_number')]

    def save(self, *args, **kwargs):
        if self.bank_account_ciphertext:
            self.bank_account_ciphertext = SensitiveValueCipher.encrypt_if_needed(self.bank_account_ciphertext)
        if self.pension_id_ciphertext:
            self.pension_id_ciphertext = SensitiveValueCipher.encrypt_if_needed(self.pension_id_ciphertext)
        if self.tax_id_ciphertext:
            self.tax_id_ciphertext = SensitiveValueCipher.encrypt_if_needed(self.tax_id_ciphertext)
        super().save(*args, **kwargs)

    def decrypt_sensitive_fields(self):
        return {
            'bank_account_ciphertext': SensitiveValueCipher.decrypt(self.bank_account_ciphertext),
            'pension_id_ciphertext': SensitiveValueCipher.decrypt(self.pension_id_ciphertext),
            'tax_id_ciphertext': SensitiveValueCipher.decrypt(self.tax_id_ciphertext),
        }

    def clean(self):
        if self.employee_id and self.company_id != self.employee.company_id:
            raise ValidationError('Payroll profile must belong to the employee company.')


class PayrollConfig(PayrollScopedModel):
    payroll_day = models.PositiveSmallIntegerField(default=25)
    leave_allowance_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    standard_working_days = models.PositiveSmallIntegerField(default=22)
    maximum_deduction_percent = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    settlement_formats = models.JSONField(default=list)

    class Meta:
        db_table = 'payroll_configs'
        constraints = [models.UniqueConstraint(fields=('company',), name='unique_payroll_config_company')]


class StatutoryRule(PayrollScopedModel):
    class Kind(models.TextChoices):
        PAYE = 'PAYE', 'PAYE'
        PENSION_EMPLOYEE = 'PENSION_EMPLOYEE', 'Employee pension'
        PENSION_EMPLOYER = 'PENSION_EMPLOYER', 'Employer pension'

    kind = models.CharField(max_length=30)
    rate_percent = models.DecimalField(max_digits=7, decimal_places=4)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'payroll_statutory_rules'


class PayrollAdjustment(PayrollScopedModel):
    class Kind(models.TextChoices):
        BONUS = 'BONUS', 'Bonus'
        ADVANCE = 'ADVANCE', 'Advance'
        LATENESS = 'LATENESS', 'Lateness'
        DRESS_CODE = 'DRESS_CODE', 'Dress code'
        KPI = 'KPI', 'KPI'
        LOAN = 'LOAN', 'Loan'
        CUSTOM = 'CUSTOM', 'Custom'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        CONTESTED = 'CONTESTED', 'Contested'
        RESOLVED = 'RESOLVED', 'Resolved'
        REJECTED = 'REJECTED', 'Rejected'

    employee = models.ForeignKey('core.Employee', on_delete=models.CASCADE, related_name='payroll_adjustments')
    kind = models.CharField(max_length=20)
    name = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    month = models.DateField()
    reason = models.TextField()
    evidence_reference = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, default=Status.PENDING)
    approved_by = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        db_table = 'payroll_adjustments'


class PayrollRun(PayrollScopedModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        CALCULATED = 'CALCULATED', 'Calculated'
        REVIEWED = 'REVIEWED', 'Reviewed'
        APPROVED = 'APPROVED', 'Approved'
        EXPORTED = 'EXPORTED', 'Exported'
        RECONCILED = 'RECONCILED', 'Reconciled'
        FAILED = 'FAILED', 'Failed'

    month = models.DateField()
    status = models.CharField(max_length=20, default=Status.DRAFT)
    total_gross = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_held = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    net_payroll = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    calculated_by = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    approved_by = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payroll_runs'
        constraints = [models.UniqueConstraint(fields=('company', 'month'), name='unique_payroll_run_month')]


class PayrollItem(PayrollScopedModel):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name='items')
    employee = models.ForeignKey('core.Employee', on_delete=models.PROTECT, related_name='payroll_items')
    base_salary = models.DecimalField(max_digits=14, decimal_places=2)
    leave_allowance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    advance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gross_pay = models.DecimalField(max_digits=14, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    held_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        db_table = 'payroll_items'
        constraints = [models.UniqueConstraint(fields=('payroll_run', 'employee'), name='unique_payroll_item_employee')]


class PayrollDeduction(PayrollScopedModel):
    payroll_item = models.ForeignKey(PayrollItem, on_delete=models.CASCADE, related_name='deductions')
    adjustment = models.ForeignKey(PayrollAdjustment, null=True, blank=True, on_delete=models.SET_NULL)
    kind = models.CharField(max_length=30)
    name = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.TextField()
    is_held = models.BooleanField(default=False)
    contested_at = models.DateTimeField(null=True, blank=True)
    contest_reason = models.TextField(blank=True)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'payroll_deductions'


class PayrollAuditEvent(PayrollScopedModel):
    payroll_run = models.ForeignKey(PayrollRun, null=True, blank=True, on_delete=models.CASCADE, related_name='audit_events')
    employee = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    details = models.JSONField(default=dict)
    actor = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        db_table = 'payroll_audit_events'


class SettlementExport(PayrollScopedModel):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name='exports')
    format = models.CharField(max_length=10)
    file_path = models.CharField(max_length=500)
    checksum = models.CharField(max_length=64)
    exported_by = models.ForeignKey('core.Employee', on_delete=models.PROTECT, related_name='+')

    class Meta:
        db_table = 'payroll_settlement_exports'


class ReconciliationRecord(PayrollScopedModel):
    payroll_run = models.OneToOneField(PayrollRun, on_delete=models.CASCADE, related_name='reconciliation')
    bank_reference = models.CharField(max_length=100)
    result = models.CharField(max_length=20)
    details = models.JSONField(default=dict)
    reconciled_by = models.ForeignKey('core.Employee', on_delete=models.PROTECT, related_name='+')

    class Meta:
        db_table = 'payroll_reconciliations'
