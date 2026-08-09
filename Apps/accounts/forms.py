from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from Apps.accounts.models import User


class CustomUserCreationForm(UserCreationForm):
    """Custom form for creating users."""
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role')


class CustomUserChangeForm(UserChangeForm):
    """Custom form for editing users."""
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')
