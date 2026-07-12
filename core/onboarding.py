from pathlib import Path
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.models import ApprovalDocument, Employee, EmployeeRole, LeaveBalance, LeaveRequest, LeaveType, OrgUnit, OnboardingStatus
from zoho.services import ZohoWorkDriveService


class ApprovalRoutingService:
    @staticmethod
    def get_leave_approvers(employee: Employee):
        approvers = []

        if employee.manager_id:
            approvers.append(employee.manager)

        org_unit = employee.org_unit
        while org_unit:
            if org_unit.head_id and org_unit.head_id != employee.manager_id:
                approvers.append(org_unit.head)
            org_unit = org_unit.parent

        if employee.company_id:
            hr_admins = Employee.objects.filter(company=employee.company, role=EmployeeRole.HR_ADMIN, deleted_at__isnull=True)
            approvers.extend(hr_admins)

        seen = set()
        unique_approvers = []
        for approver in approvers:
            if not approver or approver.pk in seen:
                continue
            seen.add(approver.pk)
            unique_approvers.append(approver)
        return unique_approvers

    @staticmethod
    def next_approver(employee: Employee):
        approvers = ApprovalRoutingService.get_leave_approvers(employee)
        return approvers[0] if approvers else None


class ApprovalDocumentService:
    @staticmethod
    def _document_dir():
        base_dir = Path(getattr(settings, 'APPROVAL_DOCUMENT_DIR', Path(settings.BASE_DIR) / 'generated_documents'))
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir

    @staticmethod
    def _write_docx(file_path: Path, title: str, lines: list[str]):
        try:
            from docx import Document
        except ImportError as exc:
            raise ValidationError('python-docx is required to generate approval documents.') from exc

        document = Document()
        document.add_heading(title, 0)
        for line in lines:
            document.add_paragraph(line)
        document.save(str(file_path))

    @staticmethod
    def create_for_leave_request(leave_request: LeaveRequest, document_type: str, actor: Employee):
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        file_name = f"{leave_request.employee.username}_{leave_request.leave_type.name}_{document_type.lower()}_{timestamp}.docx".replace(' ', '_')
        file_path = ApprovalDocumentService._document_dir() / file_name
        title = f"Leave {document_type.title()}"
        lines = [
            f"Company: {leave_request.company.name}",
            f"Employee: {leave_request.employee.get_full_name() or leave_request.employee.username}",
            f"Leave Type: {leave_request.leave_type.name}",
            f"Start Date: {leave_request.start_date}",
            f"End Date: {leave_request.end_date}",
            f"Days Requested: {leave_request.days_requested}",
            f"Status: {leave_request.status}",
            f"Reviewed By: {actor.get_full_name() or actor.username}",
            f"Reviewed At: {timezone.now()}",
            f"Reason: {leave_request.reason or '-'}",
            f"Rejection Reason: {leave_request.rejection_reason or '-'}",
        ]
        ApprovalDocumentService._write_docx(file_path, title, lines)
        return ApprovalDocument.objects.create(
            company=leave_request.company,
            leave_request=leave_request,
            document_type=document_type,
            file_name=file_name,
            file_path=str(file_path),
            created_by=actor,
        )


class OnboardingService:
    @staticmethod
    def onboard_employee(employee: Employee, created_by: Employee = None):
        if not employee.company_id:
            raise ValueError('Employee must belong to a company before onboarding.')

        employee.onboarding_status = OnboardingStatus.COMPLETE
        employee.save(update_fields=['onboarding_status', 'updated_at'])

        if getattr(employee, 'workdrive_folder', None):
            return employee.workdrive_folder

        service = ZohoWorkDriveService()
        folder = service.create_folder(
            company=employee.company,
            folder_name=f'{employee.get_full_name() or employee.username} Files',
            created_by=created_by,
            employee=employee,
        )
        return folder


class LeaveService:
    @staticmethod
    def request_leave(*, employee: Employee, leave_type: LeaveType, start_date, end_date, days_requested, reason=''):
        if employee.company_id != leave_type.company_id:
            raise ValidationError('Leave type must belong to the same company as the employee.')

        with transaction.atomic():
            leave_request = LeaveRequest.objects.create(
                company=employee.company,
                employee=employee,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                days_requested=days_requested,
                reason=reason,
                created_by=employee,
                updated_by=employee,
            )
            return leave_request

    @staticmethod
    def approve_leave(leave_request: LeaveRequest, reviewed_by: Employee):
        if reviewed_by.company_id != leave_request.company_id:
            raise ValidationError('Reviewer must belong to the same company.')

        with transaction.atomic():
            leave_request.status = LeaveRequest.Status.APPROVED
            leave_request.reviewed_by = reviewed_by
            leave_request.reviewed_at = timezone.now()
            leave_request.updated_by = reviewed_by
            leave_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_by', 'updated_at'])

            balance, _ = LeaveBalance.objects.get_or_create(
                company=leave_request.company,
                employee=leave_request.employee,
                leave_type=leave_request.leave_type,
                defaults={'allocated_days': leave_request.leave_type.default_days},
            )
            balance.used_days += leave_request.days_requested
            balance.updated_by = reviewed_by
            balance.save(update_fields=['used_days', 'updated_by', 'updated_at'])
            ApprovalDocumentService.create_for_leave_request(leave_request, ApprovalDocument.DocumentType.APPROVAL, reviewed_by)
            return leave_request

    @staticmethod
    def reject_leave(leave_request: LeaveRequest, reviewed_by: Employee, reason=''):
        if reviewed_by.company_id != leave_request.company_id:
            raise ValidationError('Reviewer must belong to the same company.')

        leave_request.status = LeaveRequest.Status.REJECTED
        leave_request.reviewed_by = reviewed_by
        leave_request.reviewed_at = timezone.now()
        leave_request.rejection_reason = reason
        leave_request.updated_by = reviewed_by
        leave_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'updated_by', 'updated_at'])
        ApprovalDocumentService.create_for_leave_request(leave_request, ApprovalDocument.DocumentType.REJECTION, reviewed_by)
        return leave_request

    @staticmethod
    def cancel_leave(leave_request: LeaveRequest, cancelled_by: Employee):
        if cancelled_by.company_id != leave_request.company_id:
            raise ValidationError('Canceller must belong to the same company.')

        leave_request.status = LeaveRequest.Status.CANCELLED
        leave_request.updated_by = cancelled_by
        leave_request.save(update_fields=['status', 'updated_by', 'updated_at'])
        ApprovalDocumentService.create_for_leave_request(leave_request, ApprovalDocument.DocumentType.CANCELLATION, cancelled_by)
        return leave_request
