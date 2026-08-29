from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from Apps.common.models import BaseModel
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from wagtail.images.blocks import ImageChooserBlock
from django.shortcuts import redirect, render
from django.contrib.auth import login as auth_login


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.SUPER_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, BaseModel):
    """Custom user model with email-based authentication and roles."""
    
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', _('Super Admin')
        ADMIN = 'admin', _('Admin')
        EDITOR = 'editor', _('Editor')

    username = None  # Remove username field
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EDITOR,
        verbose_name=_('Role')
    )
    first_name = models.CharField(max_length=150, verbose_name=_('First Name'))
    last_name = models.CharField(max_length=150, verbose_name=_('Last Name'))
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Phone'))
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name=_('Avatar'))
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name



class LoginPage(Page):
    heading = models.CharField(max_length=120, blank=True, default="Welcome Back")
    subtext = models.CharField(max_length=200, blank=True, default="Login to manage your blogs")
    submit_button_text = models.CharField(max_length=50, blank=True, default="Login")
    register_prompt_text = models.CharField(max_length=100, blank=True, default="Don't have an account?")
    register_link_text = models.CharField(max_length=50, blank=True, default="Register")
    background_image = models.ForeignKey(
        "wagtailimages.Image", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    content_panels = Page.content_panels + [
        FieldPanel("heading"),
        FieldPanel("subtext"),
        FieldPanel("submit_button_text"),
        FieldPanel("register_prompt_text"),
        FieldPanel("register_link_text"),
        FieldPanel("background_image"),
    ]

    parent_page_types = ["companies.CompanyHomePage", "wagtailcore.Page"]
    subpage_types = []
    template = "accounts/login_page.html"

    def serve(self, request):
        from Apps.accounts.forms import EmailLoginForm
        from Apps.accounts.models import RegisterPage

        form = EmailLoginForm(request, data=request.POST or None)
        if request.method == "POST" and form.is_valid():
            auth_login(request, form.get_user())
            return redirect("/")

        context = self.get_context(request)
        context["form"] = form
        register_page = RegisterPage.objects.live().first()
        context["register_url"] = register_page.url if register_page else "/register/"
        return render(request, self.template, context)

    class Meta:
        verbose_name = "Login Page"
        
          
class RegisterPage(Page):
    heading = models.CharField(max_length=120, blank=True, default="Create Your Account")
    subtext = models.CharField(max_length=200, blank=True, default="Get started with BlogPro")

    email_label = models.CharField(max_length=50, blank=True, default="Email address")
    first_name_label = models.CharField(max_length=50, blank=True, default="First Name")
    last_name_label = models.CharField(max_length=50, blank=True, default="Last Name")
    role_label = models.CharField(max_length=50, blank=True, default="Role")
    password_label = models.CharField(max_length=50, blank=True, default="Password")
    confirm_password_label = models.CharField(max_length=50, blank=True, default="Confirm Password")
    submit_button_text = models.CharField(max_length=50, blank=True, default="Register")
    login_prompt_text = models.CharField(max_length=100, blank=True, default="Already have an account?")
    login_link_text = models.CharField(max_length=50, blank=True, default="Login")
    
    background_image = models.ForeignKey(
        "wagtailimages.Image", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    content_panels = Page.content_panels + [
        FieldPanel("heading"),
        FieldPanel("subtext"),
        FieldPanel("email_label"),
        FieldPanel("first_name_label"),
        FieldPanel("last_name_label"),
        FieldPanel("role_label"),
        FieldPanel("password_label"),
        FieldPanel("confirm_password_label"),
        FieldPanel("submit_button_text"),
        FieldPanel("login_prompt_text"),
        FieldPanel("login_link_text"),
        FieldPanel("background_image"),
    ]

    parent_page_types = ["companies.CompanyHomePage", "wagtailcore.Page"]
    subpage_types = []
    template = "accounts/register_page.html"

    def serve(self, request):
        from Apps.accounts.forms import CustomUserCreationForm
        from Apps.accounts.models import LoginPage

        form = CustomUserCreationForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect("/")

        context = self.get_context(request)
        context["form"] = form
        login_page = LoginPage.objects.live().first()
        context["login_url"] = login_page.url if login_page else "/login/"
        return render(request, self.template, context)

    class Meta:
        verbose_name = "Register Page"