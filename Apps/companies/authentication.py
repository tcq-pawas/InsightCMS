from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from Apps.companies.models import Company


class CompanyAPIKeyAuthentication(BaseAuthentication):
    """
    X-API-Key header se company resolve karta hai.
    Sirf status='active' wali company allow hogi.
    """
    def authenticate(self, request):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return None  # DRF permission class 401 dega

        try:
            company = Company.objects.get(
                api_key=api_key,
                status=Company.Status.ACTIVE,
            )
        except Company.DoesNotExist:
            raise AuthenticationFailed("Invalid or inactive API key")

        return (company, None)  # request.user = company object


class IsAuthenticatedCompany:
    """Permission class — agar authenticate() None return kare to 401."""
    def has_permission(self, request, view):
        return request.user is not None and not isinstance(request.user, type(None))