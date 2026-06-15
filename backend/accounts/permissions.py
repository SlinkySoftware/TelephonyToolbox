from rest_framework.permissions import BasePermission

from accounts.models import UserRole


class IsAppAdmin(BasePermission):
    message = 'App Admin access is required.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == UserRole.APP_ADMIN)