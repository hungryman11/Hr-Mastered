import csv
import hashlib
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from core.models import (EmployeeRole, LeaveRequest, PayrollAdjustment, PayrollAuditEvent,
                         PayrollConfig, PayrollDeduction, PayrollItem, PayrollProfile,
                         PayrollRun, ReconciliationRecord, SettlementExport, StatutoryRule)
from core.onboarding import LeaveService


MONEY = Decimal('0.01')


def money(value):
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


class PayrollService:
    @staticmethod
    def _audit(run, action, actor, **details):
        PayrollAuditEvent.objects.create(company=run.company, payroll_run=run, action=action, actor=actor, details=details, created_by=actor, updated_by=actor)

    @staticmethod
    def calculate(run, actor):
        if run.status != PayrollRun.Status.DRAFT:
            raise ValidationError('Only a draft payroll run can be calculated.')
        if actor.company_id != run.company_id or actor.role != EmployeeRole.HR_ADMIN:
            raise ValidationError('Only an HR administrator in this company may calculate payroll.')
        profiles = PayrollProfile.objects.select_related('employee').filter(company=run.company, employment_status=PayrollProfile.EmploymentStatus.ACTIVE)
        if not profiles.exists():
            raise ValidationError('No active payroll profiles exist for this company.')
        config, _ = PayrollConfig.objects.get_or_create(company=run.company, defaults={'settlement_formats': ['CSV', 'XLSX', 'PDF']})
        if config.standard_working_days <= 0:
            raise ValidationError('Payroll configuration must have at least one standard working day.')
        if config.maximum_deduction_percent < 0 or config.maximum_deduction_percent > 100:
            raise ValidationError('Payroll maximum deduction percent must be between 0 and 100.')
        month_start = run.month.replace(day=1)
        month_end = run.month.replace(day=monthrange(run.month.year, run.month.month)[1])
        with transaction.atomic():
            for profile in profiles:
                employee = profile.employee
                if not profile.bank_account_ciphertext or not profile.bank_code:
                    raise ValidationError(f'Payroll profile for {employee.username} is missing bank settlement details.')
                approved_leaves = LeaveRequest.objects.filter(employee=employee, status=LeaveRequest.Status.APPROVED, start_date__lte=month_end, end_date__gte=month_start)
                leave_days = sum(LeaveService.calculate_working_days(max(l.start_date, month_start), min(l.end_date, month_end), run.company) for l in approved_leaves)
                base = money(profile.base_salary)
                leave_allowance = money(base / config.standard_working_days * leave_days * config.leave_allowance_percent / 100)
                adjustments = PayrollAdjustment.objects.filter(company=run.company, employee=employee, month=month_start, status__in=[PayrollAdjustment.Status.APPROVED, PayrollAdjustment.Status.CONTESTED])
                bonus = money(sum((a.amount for a in adjustments.filter(kind=PayrollAdjustment.Kind.BONUS)), Decimal()))
                advance = money(sum((a.amount for a in adjustments.filter(kind=PayrollAdjustment.Kind.ADVANCE)), Decimal()))
                gross = money(base + leave_allowance + bonus + advance)
                item = PayrollItem.objects.create(company=run.company, payroll_run=run, employee=employee, base_salary=base, leave_allowance=leave_allowance, bonus=bonus, advance=advance, gross_pay=gross, net_pay=gross, created_by=actor, updated_by=actor)
                deductions, held = [], Decimal()
                for rule in StatutoryRule.objects.filter(company=run.company, is_active=True, effective_from__lte=month_start).filter(models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=month_start)):
                    if rule.kind == StatutoryRule.Kind.PENSION_EMPLOYER:
                        continue
                    deductions.append((rule.kind, rule.kind.replace('_', ' '), money(gross * rule.rate_percent / 100), 'Finance-configured statutory rule', False, None))
                for adj in adjustments.exclude(kind__in=[PayrollAdjustment.Kind.BONUS, PayrollAdjustment.Kind.ADVANCE]):
                    held_flag = adj.status == PayrollAdjustment.Status.CONTESTED
                    deductions.append((adj.kind, adj.name, money(adj.amount), adj.reason, held_flag, adj))
                ceiling = money(gross * config.maximum_deduction_percent / 100)
                applied = Decimal()
                for kind, name, amount, reason, held_flag, adj in deductions:
                    amount = min(amount, max(Decimal(), ceiling - applied))
                    applied += amount
                    held += amount if held_flag else Decimal()
                    PayrollDeduction.objects.create(company=run.company, payroll_item=item, adjustment=adj, kind=kind, name=name, amount=amount, reason=reason, is_held=held_flag, created_by=actor, updated_by=actor)
                if applied < sum((amount for _, _, amount, _, _, _ in deductions), Decimal()):
                    PayrollService._audit(run, 'deductions_capped', actor, employee_id=employee.id, cap=str(ceiling), applied=str(applied))
                item.total_deductions, item.held_amount, item.net_pay = money(applied), money(held), money(max(Decimal(), gross - applied))
                item.save(update_fields=['total_deductions', 'held_amount', 'net_pay', 'updated_at'])
            totals = run.items.aggregate(gross=models.Sum('gross_pay'), deductions=models.Sum('total_deductions'), held=models.Sum('held_amount'), net=models.Sum('net_pay'))
            run.total_gross, run.total_deductions, run.total_held, run.net_payroll = (money(totals[k] or 0) for k in ('gross', 'deductions', 'held', 'net'))
            run.status, run.calculated_by, run.updated_by = PayrollRun.Status.CALCULATED, actor, actor
            run.save()
            PayrollService._audit(run, 'payroll_calculated', actor, employee_count=run.items.count(), net=str(run.net_payroll))
        return run

    @staticmethod
    def review_or_approve(run, actor, approve=False):
        if actor.company_id != run.company_id or actor.role != EmployeeRole.FINANCE:
            raise ValidationError('Only a finance approver in this company may review payroll.')
        if actor.id == run.calculated_by_id:
            raise ValidationError('The payroll maker cannot review or approve their own run.')
        required = PayrollRun.Status.REVIEWED if approve else PayrollRun.Status.CALCULATED
        if run.status != required:
            raise ValidationError(f'Payroll run must be {required.lower()} before this action.')
        run.status = PayrollRun.Status.APPROVED if approve else PayrollRun.Status.REVIEWED
        if approve:
            run.approved_by, run.approved_at = actor, timezone.now()
        run.updated_by = actor
        run.save()
        PayrollService._audit(run, 'payroll_approved' if approve else 'payroll_reviewed', actor)
        return run

    @staticmethod
    def reconcile(run, actor, bank_reference, result, details):
        if actor.company_id != run.company_id or actor.role != EmployeeRole.FINANCE or run.status != PayrollRun.Status.EXPORTED:
            raise ValidationError('Only the finance team of this company may reconcile an exported payroll run.')
        ReconciliationRecord.objects.update_or_create(payroll_run=run, defaults={'company': run.company, 'bank_reference': bank_reference, 'result': result, 'details': details, 'reconciled_by': actor, 'created_by': actor, 'updated_by': actor})
        run.status, run.updated_by = (PayrollRun.Status.RECONCILED if result == 'SUCCESS' else PayrollRun.Status.FAILED), actor
        run.save()
        PayrollService._audit(run, 'payroll_reconciled', actor, bank_reference=bank_reference, result=result)
        return run

    @staticmethod
    def contest_deduction(deduction, employee, reason):
        if deduction.payroll_item.employee_id != employee.id:
            raise ValidationError('Only the affected employee may contest this deduction.')
        if not reason or not reason.strip():
            raise ValidationError({'reason': 'A dispute reason is required.'})
        if deduction.payroll_item.payroll_run.status in {PayrollRun.Status.EXPORTED, PayrollRun.Status.RECONCILED}:
            raise ValidationError('Exported or reconciled deductions cannot be contested.')
        deduction.is_held = True
        deduction.contested_at = timezone.now()
        deduction.contest_reason = reason.strip()
        deduction.save(update_fields=['is_held', 'contested_at', 'contest_reason', 'updated_at'])
        item = deduction.payroll_item
        item.held_amount = money(item.deductions.filter(is_held=True).aggregate(total=models.Sum('amount'))['total'] or 0)
        item.save(update_fields=['held_amount', 'updated_at'])
        PayrollService._audit(item.payroll_run, 'deduction_contested', employee, deduction_id=deduction.id, reason=reason.strip())
        return deduction

    @staticmethod
    def resolve_deduction(deduction, finance_user, uphold, notes):
        if finance_user.role != EmployeeRole.FINANCE or finance_user.company_id != deduction.company_id:
            raise ValidationError('Only Finance may resolve a deduction dispute.')
        if not deduction.is_held or not deduction.contested_at:
            raise ValidationError('Only a contested deduction can be resolved.')
        if not notes or not notes.strip():
            raise ValidationError({'notes': 'Resolution notes are required.'})
        item = deduction.payroll_item
        if item.payroll_run.status not in {PayrollRun.Status.CALCULATED, PayrollRun.Status.REVIEWED}:
            raise ValidationError('This deduction can no longer be resolved at the current payroll stage.')
        deduction.is_held = False
        deduction.resolution_notes = notes.strip()
        if not uphold:
            deduction.amount = Decimal()
        deduction.save(update_fields=['is_held', 'resolution_notes', 'amount', 'updated_at'])
        item.total_deductions = money(item.deductions.aggregate(total=models.Sum('amount'))['total'] or 0)
        item.held_amount = money(item.deductions.filter(is_held=True).aggregate(total=models.Sum('amount'))['total'] or 0)
        item.net_pay = money(max(Decimal(), item.gross_pay - item.total_deductions))
        item.save(update_fields=['total_deductions', 'held_amount', 'net_pay', 'updated_at'])
        run = item.payroll_run
        run.total_deductions = money(run.items.aggregate(total=models.Sum('total_deductions'))['total'] or 0)
        run.total_held = money(run.items.aggregate(total=models.Sum('held_amount'))['total'] or 0)
        run.net_payroll = money(run.items.aggregate(total=models.Sum('net_pay'))['total'] or 0)
        run.save(update_fields=['total_deductions', 'total_held', 'net_payroll', 'updated_at'])
        PayrollService._audit(run, 'deduction_resolved', finance_user, deduction_id=deduction.id, upheld=uphold)
        return deduction

    @staticmethod
    def export(run, actor, export_format):
        if run.status != PayrollRun.Status.APPROVED or actor.role != EmployeeRole.FINANCE or actor.id == run.calculated_by_id:
            raise ValidationError('A different finance approver must export an approved payroll run.')
        if export_format not in {'CSV', 'XLSX', 'PDF', 'PACK'}:
            raise ValidationError('Export format must be CSV, XLSX, PDF, or PACK.')
        output_dir = Path(settings.BASE_DIR) / 'generated_documents'
        output_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        for item in run.items.select_related('employee__payroll_profile'):
            profile = item.employee.payroll_profile
            rows.append([profile.employee_number, item.employee.get_full_name() or item.employee.username, profile.bank_code, str(item.net_pay), f'{run.uuid}-{item.employee_id}'])
        headers = ['employee_number', 'employee_name', 'bank_code', 'net_pay', 'reference']
        formats = ('CSV', 'XLSX', 'PDF') if export_format == 'PACK' else (export_format,)
        paths = []
        for fmt in formats:
            path = output_dir / f'payroll_{run.uuid}.{fmt.lower()}'
            if fmt == 'CSV':
                with path.open('w', newline='', encoding='utf-8') as handle:
                    writer = csv.writer(handle); writer.writerow(headers); writer.writerows(rows)
            elif fmt == 'XLSX':
                from openpyxl import Workbook
                workbook = Workbook(); sheet = workbook.active; sheet.title = 'Settlement'
                sheet.append(headers)
                for row in rows: sheet.append(row)
                workbook.save(path)
            else:
                from reportlab.lib.pagesizes import A4
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
                from reportlab.lib import colors
                from reportlab.lib.styles import getSampleStyleSheet
                document = SimpleDocTemplate(str(path), pagesize=A4)
                table = Table([headers] + rows, repeatRows=1)
                table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey), ('GRID', (0, 0), (-1, -1), 0.25, colors.grey)]))
                document.build([Paragraph(f'Payroll settlement: {run.month:%B %Y}', getSampleStyleSheet()['Heading1']), table])
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            SettlementExport.objects.create(company=run.company, payroll_run=run, format=fmt, file_path=str(path), checksum=checksum, exported_by=actor, created_by=actor, updated_by=actor)
            paths.append(path)
        run.status, run.updated_by = PayrollRun.Status.EXPORTED, actor; run.save()
        PayrollService._audit(run, 'settlement_exported', actor, formats=list(formats), files=[str(path) for path in paths])
        return paths
