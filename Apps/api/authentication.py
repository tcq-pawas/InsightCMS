from django.contrib.auth.models import AnonymousUser
from rest_framework import authentication
from rest_framework import exceptions
from Apps.companies.models import Company


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication using API Key.
    """
    
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        
        if not api_key:
            return None
        
        try:
            company = Company.objects.get(api_key=api_key, status=Company.Status.ACTIVE)
        except Company.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API key')
        
        # Attach company to request
        request.company = company
        
        # Return a tuple of (user, auth) - we use AnonymousUser since we're authenticating companies
        return (AnonymousUser(), None)
