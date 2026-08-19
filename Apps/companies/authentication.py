from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from Apps.companies.models import Company
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object


class CompanyAPIKeyAuthentication(BaseAuthentication):
    """
    X-API-Key header se company resolve karta hai.
    Sirf status='active' wali company allow hogi.
    """
    def authenticate(self, request):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return None 

        try:
            company = Company.objects.get(
                api_key=api_key,
                status=Company.Status.ACTIVE,
            )
        except Company.DoesNotExist:
            raise AuthenticationFailed("Invalid or inactive API key")

        return (company, None)  # request.user = company object
    
    def authenticate_header(self, request):
        # This tells DRF to return 401 (not 403) when auth fails
        return "X-API-Key"

class IsAuthenticatedCompany:
    """Permission class — agar authenticate() None return kare to 401."""
    def has_permission(self, request, view):
        return request.user is not None and not isinstance(request.user, type(None))
    
    
class CompanyAPIKeyScheme(OpenApiAuthenticationExtension):
    target_class = "Apps.companies.authentication.CompanyAPIKeyAuthentication"
    name = "ApiKeyAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }