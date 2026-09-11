from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm, AuthenticationForm
from Apps.accounts.models import User


class CustomUserCreationForm(UserCreationForm):
    """Custom form for creating users."""
    
    company_name = forms.CharField(max_length=150, required=True)
    website_url = forms.URLField(max_length=255, required=False)  # required=True karo agar mandatory chahiye
    admin_username = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = (
            "admin_username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
            )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Clear only help_text (password hints) — do NOT remove validators
        # Removing validators would strip Django's password-match check too
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists. Please login instead.")
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match. Please enter the same password in both fields.")
        return password2


class CustomUserChangeForm(UserChangeForm):
    """Custom form for editing users."""
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'is_active', 'is_staff')


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email')