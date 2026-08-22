from rest_framework.permissions import BasePermission


class HasValidCompanyAPIKey(BasePermission):
    message = "Valid X-API-Key header required."

    def has_permission(self, request, view):
        return getattr(request, "user", None) is not None and hasattr(request.user, "api_key")