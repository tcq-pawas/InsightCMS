from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm, AuthenticationForm
from Apps.accounts.models import User


class CustomUserCreationForm(UserCreationForm):
    """Custom form for creating users."""

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove all password validators — user can set any password
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
        for field in ['password1', 'password2']:
            self.fields[field].validators = []

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists. Please login instead.")
        return email


class CustomUserChangeForm(UserChangeForm):
    """Custom form for editing users."""
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email')