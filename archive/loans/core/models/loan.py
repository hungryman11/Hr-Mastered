from django.core.exceptions import ValidationError
from django.db import models
from .payroll import PayrollScopedModel


class LoanProduct(PayrollScopedModel):
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    class Meta: db_table = 'loan_products'; constraints = [models.UniqueConstraint(fields=('company','name'), name='unique_loan_product_name')]


class LoanChecklistTemplateItem(PayrollScopedModel):
    loan_product = models.ForeignKey(LoanProduct, on_delete=models.CASCADE, related_name='checklist_template')
    name = models.CharField(max_length=200)
    required = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    class Meta: db_table = 'loan_checklist_templates'; ordering = ('sort_order','id')


class LoanCase(PayrollScopedModel):
    class Status(models.TextChoices):
        DRAFT='DRAFT','Draft'; IN_REVIEW='IN_REVIEW','In review'; RETURNED='RETURNED','Returned'; APPROVED='APPROVED','Approved for risk review'; REJECTED='REJECTED','Rejected'; MORE_INFO='MORE_INFO','Needs more information'
    applicant = models.ForeignKey('core.Employee', on_delete=models.PROTECT, related_name='loan_cases')
    loan_product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT)
    requested_amount = models.DecimalField(max_digits=14, decimal_places=2)
    purpose = models.TextField()
    repayment_months = models.PositiveSmallIntegerField()
    collateral_type = models.CharField(max_length=100)
    collateral_value = models.DecimalField(max_digits=14, decimal_places=2)
    collateral_details = models.TextField()
    assigned_checker = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_loan_cases')
    status = models.CharField(max_length=20, default=Status.DRAFT)
    recommendation = models.TextField(blank=True)
    decision_reason = models.TextField(blank=True)
    class Meta: db_table = 'loan_cases'


class LoanCaseChecklistItem(PayrollScopedModel):
    class Status(models.TextChoices): RECEIVED='RECEIVED','Received'; MISSING='MISSING','Missing'; REJECTED='REJECTED','Rejected'; NOT_APPLICABLE='NOT_APPLICABLE','Not applicable'
    loan_case = models.ForeignKey(LoanCase, on_delete=models.CASCADE, related_name='checklist_items')
    name = models.CharField(max_length=200)
    required = models.BooleanField(default=True)
    status = models.CharField(max_length=20, default=Status.MISSING)
    evidence_reference = models.CharField(max_length=500, blank=True)
    note = models.TextField(blank=True)
    checked_by = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    checked_at = models.DateTimeField(null=True, blank=True)
    class Meta: db_table = 'loan_case_checklist_items'


class LoanAuditEvent(PayrollScopedModel):
    loan_case = models.ForeignKey(LoanCase, on_delete=models.CASCADE, related_name='audit_events')
    action = models.CharField(max_length=100)
    details = models.JSONField(default=dict)
    actor = models.ForeignKey('core.Employee', null=True, on_delete=models.SET_NULL, related_name='+')
    class Meta: db_table = 'loan_audit_events'; ordering=('-created_at',)
