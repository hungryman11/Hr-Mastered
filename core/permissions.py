from rest_framework.permissions import BasePermission

from core.models import EmployeeRole


def _same_company(user, obj):
    return bool(getattr(user, 'company_id', None) and getattr(obj, 'company_id', None) == user.company_id)


class IsCompanyMember(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.is_superuser or getattr(request.user, 'company_id', None)))

    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser or _same_company(request.user, obj)


class IsHRAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.is_superuser or request.user.role == EmployeeRole.HR_ADMIN))

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view) and (request.user.is_superuser or _same_company(request.user, obj))


class IsSuperUserOnly(BasePermission):
    """Restricted to Django superusers. Used for granting/revoking is_org_admin
    itself, so that capability can't be self-escalated or delegated further."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsOrgAdmin(BasePermission):
    """
    Gate for organogram-structure changes: org units, and any employee's
    role/manager/org_unit assignment. Deliberately narrower than IsHRAdmin so
    that an HR Admin can run day-to-day HR/leave administration without
    automatically being able to rewire the reporting structure. Only
    superusers and employees explicitly flagged `is_org_admin=True` pass.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_superuser or getattr(request.user, 'is_org_admin', False))
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view) and (request.user.is_superuser or _same_company(request.user, obj))


class IsFinanceOrHRAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_superuser or request.user.role in {EmployeeRole.HR_ADMIN, EmployeeRole.FINANCE})
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view) and (request.user.is_superuser or _same_company(request.user, obj))


class IsManagerOrHRAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_superuser or request.user.role in {EmployeeRole.HR_ADMIN, EmployeeRole.MANAGER})
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view) and (request.user.is_superuser or _same_company(request.user, obj))


class IsSelfOrManagerOrHRAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if user.role == EmployeeRole.HR_ADMIN:
            return _same_company(user, obj)
        if obj.pk == user.pk:
            return True
        if user.role == EmployeeRole.MANAGER:
            return obj.manager_id == user.pk or obj.pk in user.direct_reports.values_list('pk', flat=True)
        return False


class CanViewApprovalDecision(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.is_superuser or getattr(request.user, 'company_id', None)))

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if not _same_company(user, obj):
            return False
        if user.role == EmployeeRole.HR_ADMIN:
            return True
        leave_request = getattr(obj, 'leave_request', None)
        if not leave_request:
            return False
        if leave_request.employee_id == user.id:
            return True
        if obj.actor_id == user.id:
            return True
        return leave_request.approval_steps.filter(approver=user).exists()
