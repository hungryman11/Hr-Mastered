from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.models import Employee, EmployeeRole, LeaveBalance, LeaveRequest, LeaveType, OrgUnit
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


class OnboardingService:
    @staticmethod
    def onboard_employee(employee: Employee, created_by: Employee = None):
        if not employee.company_id:
            raise ValueError('Employee must belong to a company before onboarding.')

        employee.onboarding_status = employee.onboarding_status or 'COMPLETE'
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
        return leave_request

    @staticmethod
    def cancel_leave(leave_request: LeaveRequest, cancelled_by: Employee):
        if cancelled_by.company_id != leave_request.company_id:
            raise ValidationError('Canceller must belong to the same company.')

        leave_request.status = LeaveRequest.Status.CANCELLED
        leave_request.updated_by = cancelled_by
        leave_request.save(update_fields=['status', 'updated_by', 'updated_at'])
        return leave_request
