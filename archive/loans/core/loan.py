from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from core.models import EmployeeRole, LoanAuditEvent, LoanCase, LoanCaseChecklistItem

class LoanComplianceService:
 @staticmethod
 def audit(case, action, actor, **details): LoanAuditEvent.objects.create(company=case.company, loan_case=case, action=action, actor=actor, details=details, created_by=actor, updated_by=actor)
 @staticmethod
 def create_case(*, company, applicant, product, amount, purpose, repayment_months, collateral_type, collateral_value, collateral_details, actor):
  if amount <= 0 or collateral_value <= 0 or repayment_months <= 0: raise ValidationError('Amount, collateral value, and repayment period must be positive.')
  if applicant.company_id != company.id or product.company_id != company.id: raise ValidationError('Applicant and product must belong to the company.')
  with transaction.atomic():
   case=LoanCase.objects.create(company=company, applicant=applicant, loan_product=product, requested_amount=amount,purpose=purpose,repayment_months=repayment_months,collateral_type=collateral_type,collateral_value=collateral_value,collateral_details=collateral_details,status=LoanCase.Status.IN_REVIEW,created_by=actor,updated_by=actor)
   for item in product.checklist_template.all(): LoanCaseChecklistItem.objects.create(company=company,loan_case=case,name=item.name,required=item.required,created_by=actor,updated_by=actor)
   LoanComplianceService.audit(case,'case_created',actor,requested_amount=str(amount)); return case
 @staticmethod
 def check_item(item, checker, status, note='', evidence_reference=''):
  if checker.role != EmployeeRole.RISK_CHECKER or checker.company_id != item.company_id: raise ValidationError('Only an assigned risk checker may verify evidence.')
  if item.loan_case.assigned_checker_id not in (None, checker.id): raise ValidationError('This case is assigned to another checker.')
  if status not in {LoanCaseChecklistItem.Status.RECEIVED, LoanCaseChecklistItem.Status.MISSING, LoanCaseChecklistItem.Status.REJECTED, LoanCaseChecklistItem.Status.NOT_APPLICABLE}:
   raise ValidationError('Invalid checklist status.')
  if status in {'MISSING','REJECTED'} and not note.strip(): raise ValidationError({'note':'A note is required for missing or rejected evidence.'})
  if status == 'RECEIVED' and not evidence_reference.strip(): raise ValidationError({'evidence_reference':'Evidence reference is required.'})
  item.status = status
  item.note = note.strip()
  item.evidence_reference = evidence_reference.strip()
  item.checked_by = checker
  item.checked_at = timezone.now()
  item.save()
  LoanComplianceService.audit(item.loan_case, 'checklist_verified', checker, item_id=item.id, status=status)
  return item
 @staticmethod
 def decide(case, admin, decision, reason):
  if admin.role != EmployeeRole.COMPLIANCE_ADMIN or admin.company_id != case.company_id: raise ValidationError('Only Compliance Admin may decide a loan case.')
  if not reason.strip(): raise ValidationError({'reason':'A decision reason is required.'})
  if decision == LoanCase.Status.APPROVED and case.checklist_items.filter(required=True).exclude(status__in=['RECEIVED','NOT_APPLICABLE']).exists(): raise ValidationError('Required compliance evidence is incomplete.')
  if decision not in {LoanCase.Status.APPROVED,LoanCase.Status.RETURNED,LoanCase.Status.REJECTED,LoanCase.Status.MORE_INFO}: raise ValidationError('Invalid compliance decision.')
  case.status=decision; case.decision_reason=reason.strip(); case.updated_by=admin; case.save(); LoanComplianceService.audit(case,'case_decided',admin,decision=decision); return case
