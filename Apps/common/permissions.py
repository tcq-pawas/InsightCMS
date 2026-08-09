from rest_framework import permissions


class IsCompanyAuthenticated(permissions.BasePermission):
    """
    Permission to only allow requests from authenticated companies.
    """
    def has_permission(self, request, view):
        return request.company is not None


class IsCompanyOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner company
        return obj.company == request.company
