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


class LeaveApprovalPolicy(CompanyScopedModel):
    """Configurable leave approval policy scoped to an OrgUnit.

    The policy defines who is the first approver and who performs final HR approval.
    """
    class ApproverType(models.TextChoices):
        HEAD = 'HEAD', 'Unit Head'
        MANAGER = 'MANAGER', 'Line Manager'
        SPECIFIC = 'SPECIFIC', 'Specific Employee'
        ROLE = 'ROLE', 'Role-based'

    org_unit = models.OneToOneField('OrgUnit', on_delete=models.CASCADE, related_name='leave_policy')
    first_approver_type = models.CharField(max_length=20, choices=ApproverType.choices, default=ApproverType.HEAD)
    first_approver_employee = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='first_approver_policies')
    final_approver_type = models.CharField(max_length=20, choices=ApproverType.choices, default=ApproverType.ROLE)
    final_approver_employee = models.ForeignKey('core.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='final_approver_policies')
    # free-form JSON policy for extensible rules (e.g., branch overrides, thresholds)
    policy = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'leave_approval_policies'

    def __str__(self):
        return f'LeavePolicy: {self.org_unit.name} ({self.company.name})'


class ApprovalDelegation(CompanyScopedModel):
    """Temporary delegation of approval authority from one employee to another."""
    approver = models.ForeignKey('core.Employee', on_delete=models.CASCADE, related_name='delegations_from')
    delegate_to = models.ForeignKey('core.Employee', on_delete=models.CASCADE, related_name='delegations_to')
    start_date = models.DateField()
    end_date = models.DateField()
    active = models.BooleanField(default=True)
    reason = models.TextField(blank=True)

    class Meta:
        db_table = 'approval_delegations'

    def __str__(self):
        return f'Delegate {self.approver} → {self.delegate_to} ({self.start_date}→{self.end_date})'
