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
