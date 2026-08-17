from rest_framework.permissions import BasePermission, SAFE_METHODS
from core.models import EmployeeRole


class IsHrOrReadOnly(BasePermission):
    """Allow read-only access to anyone, but write access only to HR admins."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = getattr(request, 'user', None)
        return user is not None and getattr(user, 'role', None) == EmployeeRole.HR_ADMIN
