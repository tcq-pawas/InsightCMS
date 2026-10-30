from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from Apps.common.models import BaseModel
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import StreamField, RichTextField
from django.shortcuts import redirect, render
from django.contrib.auth import login as auth_login

# Import our custom dashboard blocks from blocks.py
from Apps.accounts.blocks import (
    SidebarLinkBlock,
    StatCardBlock,
    DashboardBodyStreamBlock,
)


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.SUPER_ADMIN)
        extra_fields.setdefault('is_approved', True) 
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, BaseModel):
    """Custom user model with email-based authentication and roles."""
    
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', _('Super Admin')
        COMPANY_ADMIN = 'company_admin', _('Company Admin')
        COMPANY_USER = 'company_user', _('Company User')

    username = None
    email = models.EmailField(_('email address'), unique=True)
    
    company_name = models.CharField(max_length=150, blank=True, default="", verbose_name=_('Company Name'))
    website_url = models.URLField(max_length=255, blank=True, null=True, verbose_name=_('Website URL'))
    admin_username = models.CharField(max_length=100, blank=True, default="", verbose_name=_('Admin/User Name'))
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.COMPANY_USER,
        verbose_name=_('Role')
    )
    first_name = models.CharField(max_length=150, verbose_name=_('First Name'))
    last_name = models.CharField(max_length=150, verbose_name=_('Last Name'))
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Phone'))
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name=_('Avatar'))
    is_approved = models.BooleanField(default=False, verbose_name=_('Approved by Super Admin'))
    is_blocked  = models.BooleanField(default=False, verbose_name=_('Blocked by Admin'))
     
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'company_name', 'admin_username']

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
        from Apps.companies.models import UserProfile

        # If user is already logged in render to dashboard
        if request.user.is_authenticated:
            return redirect("/dashboard/")

        form = EmailLoginForm(request, data=request.POST or None)
        if request.method == "POST" and form.is_valid():
            # 1. Check credentials & authenticate
            user = form.get_user()
            
            # Check if user is blocked
            if getattr(user, 'is_blocked', False):
                from django.contrib import messages
                messages.error(request, "Your account has been blocked by the administrator. Please contact support.")
                context = self.get_context(request)
                context["form"] = form
                register_page = RegisterPage.objects.live().first()
                context["register_url"] = register_page.url if register_page else "/register/"
                return render(request, self.template, context)

            # Super Admin approval is ONLY required for newly registered Company Admins
            # Company Users (writers/employees created by Company Admin) or Super Admins can login directly
            is_company_admin = (user.role == User.Role.COMPANY_ADMIN)
            if is_company_admin and not user.is_approved and not user.is_superuser:
                from django.contrib import messages
                messages.error(request, "Your company account is pending Super Admin approval. Please wait for confirmation.")
                context = self.get_context(request)
                context["form"] = form
                register_page = RegisterPage.objects.live().first()
                context["register_url"] = register_page.url if register_page else "/register/"
                return render(request, self.template, context)
            
            auth_login(request, user)

            # 2. Find user's company (for session / verification)
            from Apps.accounts.models import User as UserModel
            profile = UserProfile.objects.filter(user=user).select_related('company').first()
            if profile and profile.company:
                request.session['active_company_id'] = str(profile.company.id)
                request.session['active_company_name'] = profile.company.company_name
            elif user.role == UserModel.Role.SUPER_ADMIN:
                # Clear any leftover session from a previously logged-in company user
                request.session.pop('active_company_id', None)
                request.session.pop('active_company_name', None)

            # 3. Open dashboard of that company
            return redirect("/dashboard/")

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
    
    company_name_label = models.CharField(max_length=50, blank=True, default="Company Name")
    website_url_label = models.CharField(max_length=50, blank=True, default="Website URL")
    admin_username_label = models.CharField(max_length=50, blank=True, default="Admin/User Name")
    
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
        FieldPanel("company_name_label"),
        FieldPanel("website_url_label"),
        FieldPanel("admin_username_label"),
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
        from Apps.companies.models import Company, CompanyMembership, UserProfile

        # If already logged in, go to dashboard
        if request.user.is_authenticated:
            return redirect('/dashboard/')

        form = CustomUserCreationForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            from django.db import transaction
            from Apps.common.helpers import generate_api_key, generate_unique_slug

            with transaction.atomic():
                # Step A: Create company
                comp_name = form.cleaned_data['company_name']
                web_url = form.cleaned_data.get('website_url') or "https://example.com"
                user_email = form.cleaned_data.get('email')
                contact_p = f"{form.cleaned_data.get('first_name', '')} {form.cleaned_data.get('last_name', '')}".strip() or comp_name

                company = Company.objects.create(
                    company_name=comp_name,
                    website_name=comp_name,
                    website_url=web_url,
                    email=user_email,
                    contact_person=contact_p,
                    status="active",
                    api_key=generate_api_key(32),
                    slug=generate_unique_slug(Company, comp_name, slug_field='slug'),
                )
                
                # Step B: Create User
                user = form.save(commit=False)
                user.company_name = comp_name
                user.website_url = web_url
                user.role = User.Role.COMPANY_ADMIN
                user.is_staff = True  # Allows access to Wagtail CMS admin panel
                user.is_active = True
                user.is_approved = False # Dashboard not opens without approval
                user.save()
                
                # Step C: Connect user to company (via CompanyMembership and UserProfile)
                CompanyMembership.objects.create(
                    user=user,
                    company=company,
                    role=CompanyMembership.Role.MANAGER
                )
                UserProfile.objects.get_or_create(
                    user=user,
                    defaults={'company': company}
                )
                
            # auth_login(request, user)
            # return redirect("/dashboard/")
            
            from django.contrib import messages
            messages.success(request, "Registration successful! Your account is pending Super Admin approval. You'll be able to login once approved.")
            login_page = LoginPage.objects.live().first()
            return redirect(login_page.url if login_page else '/login/')

        context = self.get_context(request)
        context["form"] = form
        login_page = LoginPage.objects.live().first()
        context["login_url"] = login_page.url if login_page else "/login/"
        return render(request, self.template, context)

    class Meta:
        verbose_name = "Register Page"


# =========================================================================
# UserDashboardPage — StreamField-driven Modular Dashboard
# =========================================================================
class UserDashboardPage(Page):
    """Wagtail CMS-managed Dashboard Page using reusable blocks from blocks.py."""
    
    # 1. Header & Brand
    brand_name = models.CharField(max_length=100, blank=True, default="BlogPro")
    welcome_heading = models.CharField(max_length=150, blank=True, default="Dashboard")
    welcome_subtext = models.CharField(max_length=255, blank=True, default="Welcome back! Here's what's happening with your blog.")
    new_post_button_text = models.CharField(max_length=50, blank=True, default="+ New Post")
    new_post_button_url = models.CharField(max_length=255, blank=True, default="/cms/pages/")

    # 2. Dynamic StreamFields for Modular Sections
    sidebar_links = StreamField(
        [('link', SidebarLinkBlock())],
        blank=True,
        use_json_field=True,
        help_text="Dynamic Sidebar Navigation Links"
    )

    stat_cards = StreamField(
        [('stat', StatCardBlock())],
        blank=True,
        use_json_field=True,
        help_text="Top Stat Cards (Optional StreamField)"
    )

    # 5 Top Stat Cards (Direct Easy Fields)
    stat1_label = models.CharField(max_length=50, blank=True, default="Total Posts")
    stat1_value = models.CharField(max_length=50, blank=True, default="128")
    stat1_growth = models.CharField(max_length=50, blank=True, default="12.5%")

    stat2_label = models.CharField(max_length=50, blank=True, default="Total Views")
    stat2_value = models.CharField(max_length=50, blank=True, default="24.5K")
    stat2_growth = models.CharField(max_length=50, blank=True, default="18.6%")

    stat3_label = models.CharField(max_length=50, blank=True, default="Comments")
    stat3_value = models.CharField(max_length=50, blank=True, default="320")
    stat3_growth = models.CharField(max_length=50, blank=True, default="8.2%")

    stat4_label = models.CharField(max_length=50, blank=True, default="Subscribers")
    stat4_value = models.CharField(max_length=50, blank=True, default="1.2K")
    stat4_growth = models.CharField(max_length=50, blank=True, default="15.3%")

    stat5_label = models.CharField(max_length=50, blank=True, default="Published Posts")
    stat5_value = models.CharField(max_length=50, blank=True, default="98")
    stat5_growth = models.CharField(max_length=50, blank=True, default="10.1%")

    # Stat Card Bottom Caption (e.g. vs last month)
    stat_caption = models.CharField(max_length=50, blank=True, default="vs last month")

    # 3. Topbar Settings
    search_placeholder = models.CharField(max_length=100, blank=True, default="Search anything...")
    search_shortcut = models.CharField(max_length=20, blank=True, default="⌘K")
    notification_count = models.CharField(max_length=10, blank=True, default="3")

    # 4. Upgrade Banner & Sidebar Card
    show_upgrade_banner = models.BooleanField(default=True)
    upgrade_banner_title = models.CharField(max_length=200, blank=True, default="Ready to take your blog to the next level?")
    upgrade_banner_text = models.CharField(max_length=255, blank=True, default="Upgrade to BlogPro Pro and unlock powerful features.")
    upgrade_banner_button_text = models.CharField(max_length=50, blank=True, default="Upgrade Now")
    upgrade_banner_button_url = models.CharField(max_length=255, blank=True, default="#")

    sidebar_upgrade_title = models.CharField(max_length=100, blank=True, default="Upgrade to Pro")
    sidebar_upgrade_text = models.CharField(max_length=200, blank=True, default="Unlock advanced features and grow your blog faster.")
    sidebar_upgrade_button_text = models.CharField(max_length=50, blank=True, default="Upgrade Now")

    # 5. Views Overview & Recent Posts
    views_chart_heading = models.CharField(max_length=150, blank=True, default="Views Overview")
    views_chart_subtext = models.CharField(max_length=255, blank=True, default="Daily visitors over the last 30 days")
    views_filter_1 = models.CharField(max_length=50, blank=True, default="30 Days")
    views_filter_2 = models.CharField(max_length=50, blank=True, default="7 Days")
    views_filter_3 = models.CharField(max_length=50, blank=True, default="All Time")

    recent_posts_heading = models.CharField(max_length=150, blank=True, default="Writers & Authors Summary", verbose_name="Table Heading")
    recent_posts_subtext = models.CharField(max_length=255, blank=True, default="Overview of team members and their published blog contributions", verbose_name="Table Subtitle")
    view_all_posts_text = models.CharField(max_length=50, blank=True, default="Manage Team →", verbose_name="Action Link Text")
    view_all_posts_url = models.CharField(max_length=255, blank=True, default="/settings/#team", verbose_name="Action Link URL")

    # Writers Table Column Headers (Fully Dynamic from Wagtail)
    th_post_title = models.CharField(max_length=50, blank=True, default="AUTHOR / WRITER", verbose_name="Column 1 (Writer Name)")
    th_category = models.CharField(max_length=50, blank=True, default="EMAIL", verbose_name="Column 2 (Email)")
    th_views = models.CharField(max_length=50, blank=True, default="TOTAL POSTS", verbose_name="Column 3 (Total Posts)")
    th_status = models.CharField(max_length=50, blank=True, default="PUBLISHED", verbose_name="Column 4 (Published)")
    th_date = models.CharField(max_length=50, blank=True, default="UNPUBLISHED", verbose_name="Column 5 (Unpublished)")
    th_actions = models.CharField(max_length=50, blank=True, default="STATUS", verbose_name="Column 6 (Status)")
    empty_posts_text = models.CharField(max_length=100, blank=True, default="No writers found in your company.", verbose_name="Empty Table Message")
    empty_create_btn_text = models.CharField(max_length=50, blank=True, default="Invite Team Member", verbose_name="Empty Button Text")

    # Employee Blogs Table Configuration (Employee View on Dashboard)
    emp_blogs_heading = models.CharField(max_length=150, blank=True, default="My Blogs & Articles", verbose_name="Employee Table Heading")
    emp_blogs_subtext = models.CharField(max_length=255, blank=True, default="Track all blogs written by you and their approval status", verbose_name="Employee Table Subtitle")
    emp_write_blog_btn_text = models.CharField(max_length=50, blank=True, default="Write New Blog", verbose_name="Employee: Write Blog Button Text")
    emp_write_blog_btn_url = models.CharField(max_length=255, blank=True, default="", verbose_name="Employee: Write Blog URL (leave blank for default)")
    emp_th_blog_title = models.CharField(max_length=50, blank=True, default="BLOG TITLE", verbose_name="Employee: Column Blog Title")
    emp_th_description = models.CharField(max_length=50, blank=True, default="DESCRIPTION", verbose_name="Employee: Column Description")
    emp_th_status = models.CharField(max_length=50, blank=True, default="STATUS", verbose_name="Employee: Column Status")
    emp_status_rejected = models.CharField(max_length=50, blank=True, default="Approval Rejected", verbose_name="Employee Badge: Rejected")
    emp_status_approved = models.CharField(max_length=50, blank=True, default="Approved", verbose_name="Employee Badge: Approved")
    emp_status_pending = models.CharField(max_length=50, blank=True, default="Waiting for Approval", verbose_name="Employee Badge: Pending")
    emp_no_description_text = models.CharField(max_length=100, blank=True, default="No description provided", verbose_name="Employee: No Description Fallback")
    emp_empty_blogs_text = models.CharField(max_length=150, blank=True, default="You haven't written any blogs yet.", verbose_name="Employee: Empty Message")
    emp_empty_create_btn_text = models.CharField(max_length=50, blank=True, default="Create Your First Blog", verbose_name="Employee: Empty Create Button Text")

    # 6. Audience Overview
    audience_heading = models.CharField(max_length=150, blank=True, default="Audience Overview")
    audience_subtext = models.CharField(max_length=255, blank=True, default="Where your readers come from and how they browse")
    countries_heading = models.CharField(max_length=100, blank=True, default="Top Countries")
    country_1_name = models.CharField(max_length=50, blank=True, default="United States")
    country_1_pct = models.CharField(max_length=10, blank=True, default="42%")
    country_2_name = models.CharField(max_length=50, blank=True, default="United Kingdom")
    country_2_pct = models.CharField(max_length=10, blank=True, default="18%")
    country_3_name = models.CharField(max_length=50, blank=True, default="Germany")
    country_3_pct = models.CharField(max_length=10, blank=True, default="12%")
    country_4_name = models.CharField(max_length=50, blank=True, default="India")
    country_4_pct = models.CharField(max_length=10, blank=True, default="9%")
    country_5_name = models.CharField(max_length=50, blank=True, default="Canada")
    country_5_pct = models.CharField(max_length=10, blank=True, default="6%")
    traffic_heading = models.CharField(max_length=100, blank=True, default="Traffic Sources")
    traffic_legend_1 = models.CharField(max_length=50, blank=True, default="Organic 60%")
    traffic_legend_2 = models.CharField(max_length=50, blank=True, default="Social 20%")
    device_heading = models.CharField(max_length=100, blank=True, default="Device Types")
    device_legend_1 = models.CharField(max_length=50, blank=True, default="Desktop 60%")
    device_legend_2 = models.CharField(max_length=50, blank=True, default="Mobile 35%")

    # 7. Quick Actions, Comments & Storage
    quick_actions_heading = models.CharField(max_length=100, blank=True, default="Quick Actions")
    action_1_title = models.CharField(max_length=100, blank=True, default="Write New Post")
    action_1_desc = models.CharField(max_length=150, blank=True, default="Create and publish article")
    action_1_url = models.CharField(max_length=255, blank=True, default="/cms/pages/")
    action_2_title = models.CharField(max_length=100, blank=True, default="Upload Media")
    action_2_desc = models.CharField(max_length=150, blank=True, default="Add images and files")
    action_2_url = models.CharField(max_length=255, blank=True, default="/cms/images/")
    action_3_title = models.CharField(max_length=100, blank=True, default="Add Category")
    action_3_desc = models.CharField(max_length=150, blank=True, default="Organize your content")
    action_3_url = models.CharField(max_length=255, blank=True, default="/cms/")
    action_4_title = models.CharField(max_length=100, blank=True, default="View Analytics")
    action_4_desc = models.CharField(max_length=150, blank=True, default="Check detailed traffic stats")
    action_4_url = models.CharField(max_length=255, blank=True, default="/dashboard/")

    comments_heading = models.CharField(max_length=100, blank=True, default="Recent Comments")
    comments_subtext = models.CharField(max_length=150, blank=True, default="Latest reader interactions")
    view_all_comments_text = models.CharField(max_length=50, blank=True, default="View All")
    view_all_comments_url = models.CharField(max_length=255, blank=True, default="/cms/")

    # Comments Moderation Page Fields (Editable from Wagtail CMS /cms/)
    comments_page_title = models.CharField(max_length=150, blank=True, default="Comments", verbose_name="Comments Page Title")
    comments_page_subtext = models.CharField(max_length=255, blank=True, default="Moderate visitor comments on your blog posts.", verbose_name="Comments Page Subtitle")
    comments_page_empty_heading = models.CharField(max_length=100, blank=True, default="No comments yet", verbose_name="Empty State Title")
    comments_page_empty_subtext = models.CharField(max_length=255, blank=True, default="Visitor comments on your blog posts will appear here.", verbose_name="Empty State Subtitle")

    # Summary Cards & Filter Labels
    filter_blog_label = models.CharField(max_length=50, blank=True, default="Filter Blog:", verbose_name="Filter Dropdown Label")
    card_total_comments_label = models.CharField(max_length=50, blank=True, default="Total Comments", verbose_name="Summary Card 1: Total Comments")
    card_pending_review_label = models.CharField(max_length=50, blank=True, default="Pending Review", verbose_name="Summary Card 2: Pending Review")
    card_approved_label = models.CharField(max_length=50, blank=True, default="Approved", verbose_name="Summary Card 3: Approved")
    card_rejected_label = models.CharField(max_length=50, blank=True, default="Rejected", verbose_name="Summary Card 4: Rejected")

    # Status Tabs Labels
    tab_all_label = models.CharField(max_length=50, blank=True, default="All", verbose_name="Tab: All")
    tab_pending_label = models.CharField(max_length=50, blank=True, default="Pending", verbose_name="Tab: Pending")
    tab_approved_label = models.CharField(max_length=50, blank=True, default="Approved", verbose_name="Tab: Approved")
    tab_rejected_label = models.CharField(max_length=50, blank=True, default="Rejected", verbose_name="Tab: Rejected")

    # Comments Table Column Headers
    comments_th_author  = models.CharField(max_length=50, blank=True, default="Author",   verbose_name="Column: Author")
    comments_th_comment = models.CharField(max_length=50, blank=True, default="Comment",  verbose_name="Column: Comment")
    comments_th_post    = models.CharField(max_length=50, blank=True, default="Blog Post", verbose_name="Column: Blog Post")
    comments_th_date    = models.CharField(max_length=50, blank=True, default="Date / Time", verbose_name="Column: Date")
    comments_th_status  = models.CharField(max_length=50, blank=True, default="Status",   verbose_name="Column: Status")
    comments_th_actions = models.CharField(max_length=50, blank=True, default="Actions",  verbose_name="Column: Actions")

    # Bulk Action Bar Buttons
    bulk_delete_btn  = models.CharField(max_length=50, blank=True, default="Delete Selected", verbose_name="Bulk: Delete Button")
    bulk_reject_btn  = models.CharField(max_length=50, blank=True, default="Reject",          verbose_name="Bulk: Reject Button")
    bulk_approve_btn = models.CharField(max_length=50, blank=True, default="Approve",         verbose_name="Bulk: Approve Button")

    # Row Action Buttons
    action_reply_btn   = models.CharField(max_length=50, blank=True, default="Reply",   verbose_name="Action: Reply Button")
    action_approve_btn = models.CharField(max_length=50, blank=True, default="Approve", verbose_name="Action: Approve Button")
    action_reject_btn  = models.CharField(max_length=50, blank=True, default="Reject",  verbose_name="Action: Reject Button")

    # Status Badges
    status_badge_pending  = models.CharField(max_length=50, blank=True, default="Pending",  verbose_name="Badge: Pending")
    status_badge_approved = models.CharField(max_length=50, blank=True, default="Approved", verbose_name="Badge: Approved")
    status_badge_rejected = models.CharField(max_length=50, blank=True, default="Rejected", verbose_name="Badge: Rejected")
    team_badge_text       = models.CharField(max_length=20, blank=True, default="Team",      verbose_name="Badge: Team")

    # Reply Modal
    reply_modal_their_comment_label = models.CharField(max_length=50,  blank=True, default="Their comment:",    verbose_name="Reply Modal: Their Comment Label")
    reply_modal_your_reply_label    = models.CharField(max_length=50,  blank=True, default="Your Reply",        verbose_name="Reply Modal: Your Reply Label")
    reply_modal_placeholder         = models.CharField(max_length=100, blank=True, default="Write your reply...", verbose_name="Reply Modal: Textarea Placeholder")
    reply_modal_cancel_btn          = models.CharField(max_length=50,  blank=True, default="Cancel",            verbose_name="Reply Modal: Cancel Button")
    reply_modal_send_btn            = models.CharField(max_length=50,  blank=True, default="Send Reply",        verbose_name="Reply Modal: Send Button")

    # Delete Modal
    delete_modal_title      = models.CharField(max_length=100, blank=True, default="Delete Comment?", verbose_name="Delete Modal: Title")
    delete_modal_cancel_btn = models.CharField(max_length=50,  blank=True, default="Cancel",          verbose_name="Delete Modal: Cancel Button")
    delete_modal_confirm_btn = models.CharField(max_length=50, blank=True, default="Delete",          verbose_name="Delete Modal: Confirm Button")

    # Misc / Empty States
    all_blog_posts_option = models.CharField(max_length=50,  blank=True, default="All Blog Posts",         verbose_name="Dropdown: All Blog Posts Option")
    empty_approved_text   = models.CharField(max_length=100, blank=True, default="No approved comments yet.", verbose_name="Empty State: Approved Tab")
    empty_spam_text       = models.CharField(max_length=100, blank=True, default="No spam comments. 🎉",    verbose_name="Empty State: Spam Tab")
    blog_selector_label   = models.CharField(max_length=20,  blank=True, default="Blog:",                  verbose_name="Header: Blog Selector Label")
    comment_subtext_prefix = models.CharField(max_length=100, blank=True, default="Moderate visitor comments on your blog posts across", verbose_name="Header: Comment Subtext Prefix")

    # Comment 1
    comment_1_author = models.CharField(max_length=100, blank=True, default="Alex Johnson")
    comment_1_time = models.CharField(max_length=50, blank=True, default="10m ago")
    comment_1_text = models.TextField(blank=True, default="Great insights on Wagtail StreamFields! Really helped my team configure modular pages.")
    comment_1_post = models.CharField(max_length=150, blank=True, default="Getting Started with Wagtail CMS")

    # Comment 2
    comment_2_author = models.CharField(max_length=100, blank=True, default="Sarah Miller")
    comment_2_time = models.CharField(max_length=50, blank=True, default="2h ago")
    comment_2_text = models.TextField(blank=True, default="Could you cover custom block migrations in the next tutorial? Highly requested!")
    comment_2_post = models.CharField(max_length=150, blank=True, default="10 Tips for Better Web Performance")

    # Comment 3
    comment_3_author = models.CharField(max_length=100, blank=True, default="David Lee")
    comment_3_time = models.CharField(max_length=50, blank=True, default="1d ago")
    comment_3_text = models.TextField(blank=True, default="Clean layout and great responsiveness on mobile devices. Well done!")
    comment_3_post = models.CharField(max_length=150, blank=True, default="The Future of AI in Blogging")

    storage_heading = models.CharField(max_length=100, blank=True, default="Storage Usage")
    storage_plan_name = models.CharField(max_length=50, blank=True, default="Free Plan")
    storage_used_text = models.CharField(max_length=100, blank=True, default="3.4 GB of 5 GB used")
    storage_percent = models.CharField(max_length=20, blank=True, default="68%")

    # 8. Footer Content & Social Media Links
    footer_tagline = models.TextField(blank=True, default="The all-in-one blogging platform that helps you create, manage, and grow your blog.")
    footer_facebook_url = models.CharField(max_length=255, blank=True, default="#")
    footer_twitter_url = models.CharField(max_length=255, blank=True, default="#")
    footer_instagram_url = models.CharField(max_length=255, blank=True, default="#")
    footer_linkedin_url = models.CharField(max_length=255, blank=True, default="#")

    # Footer Column 1: PRODUCT
    footer_col1_heading = models.CharField(max_length=50, blank=True, default="PRODUCT")
    footer_col1_link1_text = models.CharField(max_length=50, blank=True, default="Features")
    footer_col1_link1_url = models.CharField(max_length=255, blank=True, default="#")
    footer_col1_link2_text = models.CharField(max_length=50, blank=True, default="Pricing")
    footer_col1_link2_url = models.CharField(max_length=255, blank=True, default="#")
    footer_col1_link3_text = models.CharField(max_length=50, blank=True, default="Blog")
    footer_col1_link3_url = models.CharField(max_length=255, blank=True, default="#")
    footer_col1_link4_text = models.CharField(max_length=50, blank=True, default="Updates")
    footer_col1_link4_url = models.CharField(max_length=255, blank=True, default="#")

    # Footer Column 2: SUPPORT
    footer_col2_heading = models.CharField(max_length=50, blank=True, default="SUPPORT")
    footer_col2_link1_text = models.CharField(max_length=50, blank=True, default="Help Center")
    footer_col2_link1_url = models.CharField(max_length=255, blank=True, default="#")
    footer_col2_link2_text = models.CharField(max_length=50, blank=True, default="Documentation")
    footer_col2_link2_url = models.CharField(max_length=255, blank=True, default="#")
    footer_col2_link3_text = models.CharField(max_length=50, blank=True, default="Contact Us")
    footer_col2_link3_url = models.CharField(max_length=255, blank=True, default="#")
    footer_col2_link4_text = models.CharField(max_length=50, blank=True, default="Community")
    footer_col2_link4_url = models.CharField(max_length=255, blank=True, default="#")

    # Footer Column 3: COMPANY
    footer_col3_heading = models.CharField(max_length=50, blank=True, default="COMPANY")
    footer_col3_link1_text = models.CharField(max_length=50, blank=True, default="About Us")
    footer_col3_link1_url = models.CharField(max_length=255, blank=True, default="#")
    footer_col3_link2_text = models.CharField(max_length=50, blank=True, default="Careers")
    footer_col3_link2_url = models.CharField(max_length=255, blank=True, default="#")
    footer_col3_link3_text = models.CharField(max_length=50, blank=True, default="Privacy Policy")
    footer_col3_link3_url = models.CharField(max_length=255, blank=True, default="#")
    footer_col3_link4_text = models.CharField(max_length=50, blank=True, default="Terms of Service")
    footer_col3_link4_url = models.CharField(max_length=255, blank=True, default="#")

    # Footer Newsletter
    newsletter_heading = models.CharField(max_length=50, blank=True, default="NEWSLETTER")
    newsletter_subtext = models.CharField(max_length=150, blank=True, default="Get the latest updates and tips for your blog.")
    newsletter_placeholder = models.CharField(max_length=100, blank=True, default="Enter your email")

    # 9. Footer Bottom & Legal Links (Fully Dynamic)
    copyright_text = models.CharField(max_length=255, blank=True, default="© 2024 BlogPro. All rights reserved.")
    privacy_policy_text = models.CharField(max_length=100, blank=True, default="Privacy Policy ›")
    privacy_policy_url = models.CharField(max_length=255, blank=True, default="#")
    terms_service_text = models.CharField(max_length=100, blank=True, default="Terms of Service ›")
    terms_service_url = models.CharField(max_length=255, blank=True, default="#")

    # 10. Analytics & Reports Page Configuration (Editable from Wagtail CMS)
    analytics_heading = models.CharField(max_length=150, blank=True, default="Analytics & Reports", verbose_name="Analytics Page Title")
    analytics_subtext = models.CharField(max_length=255, blank=True, default="Track reader views, unique visitors, referral sources, and popular articles", verbose_name="Analytics Page Subtitle")
    card_total_views_label = models.CharField(max_length=50, blank=True, default="Total Views", verbose_name="Card 1: Total Views Label")
    card_total_views_sub = models.CharField(max_length=100, blank=True, default="Recorded pageviews", verbose_name="Card 1 Subtext")
    card_unique_visitors_label = models.CharField(max_length=50, blank=True, default="Unique Visitors", verbose_name="Card 2: Unique Visitors Label")
    card_unique_visitors_sub = models.CharField(max_length=100, blank=True, default="Distinct visitor sessions", verbose_name="Card 2 Subtext")
    card_avg_views_label = models.CharField(max_length=50, blank=True, default="Avg Views / Post", verbose_name="Card 3: Avg Views Label")
    card_avg_views_sub = models.CharField(max_length=100, blank=True, default="Across published articles", verbose_name="Card 3 Subtext")
    card_live_articles_label = models.CharField(max_length=50, blank=True, default="Live Articles", verbose_name="Card 4: Live Articles Label")
    card_live_articles_sub = models.CharField(max_length=100, blank=True, default="Total articles published", verbose_name="Card 4 Subtext")
    chart_heading = models.CharField(max_length=150, blank=True, default="Daily Pageviews Trend", verbose_name="Chart Heading")
    chart_subtext = models.CharField(max_length=255, blank=True, default="Visitor readership performance over selected period", verbose_name="Chart Subtext")
    chart_badge_text = models.CharField(max_length=50, blank=True, default="Blogger-Style Stats", verbose_name="Chart Badge Text")
    popular_articles_heading = models.CharField(max_length=150, blank=True, default="Popular Articles", verbose_name="Popular Articles Table Heading")
    popular_articles_subtext = models.CharField(max_length=255, blank=True, default="Top articles ranked by visitor pageviews", verbose_name="Popular Articles Table Subtitle")
    traffic_sources_heading = models.CharField(max_length=150, blank=True, default="Traffic Sources", verbose_name="Traffic Sources Heading")
    traffic_sources_subtext = models.CharField(max_length=255, blank=True, default="Where your visitors came from", verbose_name="Traffic Sources Subtext")
    devices_heading = models.CharField(max_length=150, blank=True, default="Devices & Browsers", verbose_name="Devices & Browsers Heading")
    devices_subtext = models.CharField(max_length=255, blank=True, default="Visitor hardware & software", verbose_name="Devices & Browsers Subtext")
    filter_today_label = models.CharField(max_length=50, blank=True, default="Today", verbose_name="Filter: Today Label")
    filter_7days_label = models.CharField(max_length=50, blank=True, default="7 Days", verbose_name="Filter: 7 Days Label")
    filter_30days_label = models.CharField(max_length=50, blank=True, default="30 Days", verbose_name="Filter: 30 Days Label")
    filter_all_label = models.CharField(max_length=50, blank=True, default="All Time", verbose_name="Filter: All Time Label")
    card_conversions_label = models.CharField(max_length=50, blank=True, default="Conversions", verbose_name="Card 5: Conversions Label")
    card_conversions_sub = models.CharField(max_length=100, blank=True, default="Subscribers & Leads", verbose_name="Card 5 Subtext")
    card_conversions_badge_suffix = models.CharField(max_length=20, blank=True, default="CR", verbose_name="Card 5 Badge Suffix")
    th_article_label = models.CharField(max_length=50, blank=True, default="Article", verbose_name="Table: Article Column")
    th_author_label = models.CharField(max_length=50, blank=True, default="Author", verbose_name="Table: Author Column")
    th_views_label = models.CharField(max_length=50, blank=True, default="Views", verbose_name="Table: Views Column")
    th_leads_label = models.CharField(max_length=50, blank=True, default="Leads", verbose_name="Table: Leads Column")
    th_action_label = models.CharField(max_length=50, blank=True, default="Action", verbose_name="Table: Action Column")
    btn_view_label = models.CharField(max_length=50, blank=True, default="View", verbose_name="Button: View Label")
    no_views_text = models.CharField(max_length=200, blank=True, default="No blog views recorded yet for this period.", verbose_name="Empty Views Message")
    no_referrer_text = models.CharField(max_length=200, blank=True, default="No referrer data yet. Visits will appear here.", verbose_name="Empty Referrers Message")
    device_usage_label = models.CharField(max_length=50, blank=True, default="DEVICE USAGE", verbose_name="Device Usage Section Label")
    top_browsers_label = models.CharField(max_length=50, blank=True, default="TOP BROWSERS", verbose_name="Top Browsers Section Label")

    # 11. SEO & Growth Page Configuration (Editable from Wagtail CMS)
    seo_page_title = models.CharField(max_length=150, blank=True, default="SEO & Growth", verbose_name="SEO Page Title")
    seo_page_subtext = models.CharField(max_length=255, blank=True, default="Manage XML sitemaps, robots.txt, 301 redirects, schema markup, and search visibility", verbose_name="SEO Page Subtitle")
    seo_audit_heading = models.CharField(max_length=150, blank=True, default="On-Page SEO Health Audit", verbose_name="SEO Audit Heading")
    seo_audit_subtext = models.CharField(max_length=255, blank=True, default="Optimization check across all your blog articles", verbose_name="SEO Audit Subtitle")
    seo_card_titles_label = models.CharField(max_length=50, blank=True, default="Custom SEO Titles", verbose_name="Audit Metric 1: Titles Label")
    seo_card_descriptions_label = models.CharField(max_length=50, blank=True, default="Search Descriptions", verbose_name="Audit Metric 2: Descriptions Label")
    seo_card_og_label = models.CharField(max_length=50, blank=True, default="Featured / OG Images", verbose_name="Audit Metric 3: OG Images Label")
    seo_card_canonical_label = models.CharField(max_length=50, blank=True, default="Canonical Links Set", verbose_name="Audit Metric 4: Canonical Label")
    sitemap_card_heading = models.CharField(max_length=100, blank=True, default="XML Sitemap", verbose_name="Sitemap Card Heading")
    sitemap_card_subtext = models.CharField(max_length=255, blank=True, default="Google & Bing crawler auto-index map", verbose_name="Sitemap Card Subtitle")
    robots_card_heading = models.CharField(max_length=100, blank=True, default="Robots.txt", verbose_name="Robots.txt Card Heading")
    robots_card_subtext = models.CharField(max_length=255, blank=True, default="Crawler directives & bot control", verbose_name="Robots.txt Card Subtitle")
    redirects_table_heading = models.CharField(max_length=150, blank=True, default="Custom Redirects (301 Permanent / 302 Temporary)", verbose_name="Redirects Table Heading")
    redirects_table_subtext = models.CharField(max_length=255, blank=True, default="Blogger-style error & redirect management to prevent 404 broken links", verbose_name="Redirects Table Subtitle")

    # =========================================================================
    #  STREAMFIELD BODY (Shows (+) button with block choices)
    # =========================================================================
    body = StreamField(
        DashboardBodyStreamBlock(),
        use_json_field=True,
        blank=True,
        null=True,
        help_text="Click (+) to add, reorder, or remove Dashboard sections (Stat Cards, Charts, Posts Table, Audience, Comments, Banner)"
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("search_placeholder"),
            FieldPanel("search_shortcut"),
        ], heading="Topbar Settings (Search Bar)"),
        FieldPanel("body", heading="Dashboard Modular Blocks (Click + to Add, 🗑️ to Delete or Reorder)"),
        FieldPanel("sidebar_links", heading="Sidebar Links"),
        MultiFieldPanel([
            FieldPanel("analytics_heading"),
            FieldPanel("analytics_subtext"),
            FieldPanel("chart_heading"),
            FieldPanel("chart_subtext"),
            FieldPanel("chart_badge_text"),
            FieldPanel("card_total_views_label"),
            FieldPanel("card_total_views_sub"),
            FieldPanel("card_unique_visitors_label"),
            FieldPanel("card_unique_visitors_sub"),
            FieldPanel("card_avg_views_label"),
            FieldPanel("card_avg_views_sub"),
            FieldPanel("card_live_articles_label"),
            FieldPanel("card_live_articles_sub"),
            FieldPanel("popular_articles_heading"),
            FieldPanel("popular_articles_subtext"),
            FieldPanel("traffic_sources_heading"),
            FieldPanel("traffic_sources_subtext"),
            FieldPanel("devices_heading"),
            FieldPanel("devices_subtext"),
            FieldPanel("filter_today_label"),
            FieldPanel("filter_7days_label"),
            FieldPanel("filter_30days_label"),
            FieldPanel("filter_all_label"),
            FieldPanel("card_conversions_label"),
            FieldPanel("card_conversions_sub"),
            FieldPanel("card_conversions_badge_suffix"),
            FieldPanel("th_article_label"),
            FieldPanel("th_author_label"),
            FieldPanel("th_views_label"),
            FieldPanel("th_leads_label"),
            FieldPanel("th_action_label"),
            FieldPanel("btn_view_label"),
            FieldPanel("no_views_text"),
            FieldPanel("no_referrer_text"),
            FieldPanel("device_usage_label"),
            FieldPanel("top_browsers_label"),
        ], heading="Analytics & Reports Page Settings (Custom Headings & Labels)", classname="collapsible collapsed"),
        MultiFieldPanel([
            FieldPanel("seo_page_title"),
            FieldPanel("seo_page_subtext"),
            FieldPanel("seo_audit_heading"),
            FieldPanel("seo_audit_subtext"),
            FieldPanel("seo_card_titles_label"),
            FieldPanel("seo_card_descriptions_label"),
            FieldPanel("seo_card_og_label"),
            FieldPanel("seo_card_canonical_label"),
            FieldPanel("sitemap_card_heading"),
            FieldPanel("sitemap_card_subtext"),
            FieldPanel("robots_card_heading"),
            FieldPanel("robots_card_subtext"),
            FieldPanel("redirects_table_heading"),
            FieldPanel("redirects_table_subtext"),
        ], heading="SEO & Growth Page Settings (Custom Headings & Labels)", classname="collapsible collapsed"),
    ]
        

    parent_page_types = ["wagtailcore.Page", "companies.CompanyHomePage"]
    subpage_types = []
    template = "accounts/dashboard.html"

    def serve(self, request):
        if not request.user.is_authenticated:
            from Apps.accounts.models import LoginPage
            login_page = LoginPage.objects.live().first()
            login_url = login_page.url if login_page else '/login/'
            return redirect(login_url)
        
        from Apps.blogs.models import BlogPage
        blogs = BlogPage.objects.all().order_by('-latest_revision_created_at')[:5]

        context = self.get_context(request)
        context.update({
            'page': self,
            'sidebar_links': self.sidebar_links,
            'user': request.user,
            'recent_blogs': blogs,
        })
        return render(request, self.template, context)

    class Meta:
        verbose_name = "User Dashboard Page"
        
        
# =========================================================================
# SettingsPage — CMS-editable Settings page (Profile, Security, Team)
# =========================================================================
class SettingsPage(Page):
    """Wagtail CMS-managed Settings Page — labels editable from CMS."""

    settings_page_title = models.CharField(max_length=100, blank=True, default="Settings")
    settings_page_subtext = models.CharField(max_length=255, blank=True, default="Manage your account preferences, workspace, and security settings.")

    settings_tab_1_title = models.CharField(max_length=50, blank=True, default="Profile")
    settings_tab_4_title = models.CharField(max_length=50, blank=True, default="Security")
    settings_tab_team_title = models.CharField(max_length=50, blank=True, default="Team Members")
    settings_tab_comments_title = models.CharField(max_length=50, blank=True, default="Blog Comments")

    comments_setting_heading = models.CharField(max_length=100, blank=True, default="Comments Settings")
    comments_setting_subtext = models.CharField(max_length=255, blank=True, default="Manage global blog comment behaviors, moderation policies, and submission form fields.")
    comments_setting_btn_text = models.CharField(max_length=50, blank=True, default="Save Comment Settings")

    # General Sub-Section
    comments_gen_heading = models.CharField(max_length=100, blank=True, default="General")
    comments_gen_subtext = models.CharField(max_length=255, blank=True, default="Configure core comment status, nested replies, and display limits.")
    comments_enable_label = models.CharField(max_length=100, blank=True, default="Enable Comments")
    comments_enable_desc = models.CharField(max_length=255, blank=True, default="Allow visitors to submit comments on blog posts.")
    comments_replies_label = models.CharField(max_length=100, blank=True, default="Threaded Replies")
    comments_replies_desc = models.CharField(max_length=255, blank=True, default="Allow users and staff to reply directly to existing comments.")
    comments_per_page_label = models.CharField(max_length=100, blank=True, default="Comments Per Page")
    comments_per_page_desc = models.CharField(max_length=255, blank=True, default="Number of root comments loaded initially per post.")

    # Moderation Sub-Section
    comments_mod_heading = models.CharField(max_length=100, blank=True, default="Moderation")
    comments_mod_subtext = models.CharField(max_length=255, blank=True, default="Set automated review rules and visitor notices.")
    comments_review_all_label = models.CharField(max_length=100, blank=True, default="Review All Comments")
    comments_review_all_desc = models.CharField(max_length=255, blank=True, default="When enabled, comments go to Pending queue until approved by Admin.")
    comments_under_review_label = models.CharField(max_length=100, blank=True, default="Under-Review Notice Message")
    comments_under_review_ph = models.CharField(max_length=255, blank=True, default="Your comment has been submitted and is awaiting approval.")

    # Form Fields Sub-Section
    comments_fields_heading = models.CharField(max_length=100, blank=True, default="Form Fields")
    comments_fields_subtext = models.CharField(max_length=255, blank=True, default="Configure input requirements for comment submissions.")
    comments_name_req_label = models.CharField(max_length=100, blank=True, default="Name Field Required")
    comments_name_req_desc = models.CharField(max_length=255, blank=True, default="Visitor must enter their name to submit a comment.")
    comments_email_mode_label = models.CharField(max_length=100, blank=True, default="Email Field Requirement")
    comments_email_mode_desc = models.CharField(max_length=255, blank=True, default="Choose whether Email is required, optional, or hidden.")

    settings_profile_heading = models.CharField(max_length=100, blank=True, default="Profile Information")
    settings_profile_subtext = models.CharField(max_length=255, blank=True, default="Update your personal details and public profile presence.")
    settings_profile_avatar_btn_text = models.CharField(max_length=50, blank=True, default="Change Avatar")
    settings_profile_fname_label = models.CharField(max_length=50, blank=True, default="First Name")
    settings_profile_lname_label = models.CharField(max_length=50, blank=True, default="Last Name")
    settings_profile_email_label = models.CharField(max_length=50, blank=True, default="Email Address")
    settings_profile_email_hint = models.CharField(max_length=255, blank=True, default="Email address is managed by your system administrator.")
    settings_profile_role_label = models.CharField(max_length=50, blank=True, default="Role")
    settings_profile_btn_text = models.CharField(max_length=50, blank=True, default="Save Changes")

    settings_security_heading = models.CharField(max_length=100, blank=True, default="Security & Authentication")
    settings_security_subtext = models.CharField(max_length=255, blank=True, default="Manage your password, login security, and active sessions.")
    settings_sec_curr_pass_label = models.CharField(max_length=50, blank=True, default="Current Password")
    settings_sec_curr_pass_ph = models.CharField(max_length=50, blank=True, default="••••••••")
    settings_sec_new_pass_label = models.CharField(max_length=50, blank=True, default="New Password")
    settings_sec_new_pass_ph = models.CharField(max_length=50, blank=True, default="Enter new password")
    settings_sec_conf_pass_label = models.CharField(max_length=50, blank=True, default="Confirm New Password")
    settings_sec_conf_pass_ph = models.CharField(max_length=50, blank=True, default="Confirm new password")
    settings_security_badge_text = models.CharField(max_length=50, blank=True, default="Account Protected")
    settings_security_btn_text = models.CharField(max_length=50, blank=True, default="Update Password")
    settings_session_title = models.CharField(max_length=100, blank=True, default="Active Session")
    settings_session_desc = models.CharField(max_length=255, blank=True, default="Currently signed in from this browser.")
    settings_sec_signout_btn_text = models.CharField(max_length=50, blank=True, default="Sign Out")

    team_add_heading = models.CharField(max_length=100, blank=True, default="Add New Team Member")
    team_add_subtext = models.CharField(max_length=255, blank=True, default="Create a new Company User (Writer/Editor) for your company.")
    team_email_label = models.CharField(max_length=50, blank=True, default="Email Address *")
    team_email_ph = models.CharField(max_length=100, blank=True, default="writer@company.com")
    team_password_label = models.CharField(max_length=50, blank=True, default="Temporary Password *")
    team_password_ph = models.CharField(max_length=100, blank=True, default="Minimum 6 characters")
    team_fname_label = models.CharField(max_length=50, blank=True, default="First Name")
    team_fname_ph = models.CharField(max_length=100, blank=True, default="e.g. Rahul")
    team_lname_label = models.CharField(max_length=50, blank=True, default="Last Name")
    team_lname_ph = models.CharField(max_length=100, blank=True, default="e.g. Sharma")
    team_add_btn_text = models.CharField(max_length=50, blank=True, default="Add Company User")

    team_list_heading = models.CharField(max_length=100, blank=True, default="Current Team Members")
    team_list_subtext = models.CharField(max_length=255, blank=True, default="People with access to your company's blogs.")
    team_th_user = models.CharField(max_length=50, blank=True, default="User")
    team_th_role = models.CharField(max_length=50, blank=True, default="Role")
    team_th_email = models.CharField(max_length=50, blank=True, default="Email")
    team_th_status = models.CharField(max_length=50, blank=True, default="Status")
    team_status_active_text = models.CharField(max_length=50, blank=True, default="Active")
    team_empty_text = models.CharField(max_length=100, blank=True, default="No members found.")

    # Manage User Settings Page CMS Fields
    manage_users_page_title = models.CharField(max_length=100, blank=True, default="Manage User Settings")
    manage_users_page_subtext = models.CharField(max_length=255, blank=True, default="Add team members, configure user permissions, and manage access.")
    manage_users_btn_add_text = models.CharField(max_length=50, blank=True, default="Add New User")
    manage_users_btn_add_group = models.CharField(max_length=50, blank=True, default="New Group")
    manage_users_modal_add_user_title = models.CharField(max_length=100, blank=True, default="Add New Team Member")
    manage_users_modal_add_group_title = models.CharField(max_length=100, blank=True, default="Create New Group")
    manage_users_card_heading = models.CharField(max_length=100, blank=True, default="Team Members")
    manage_users_th_user = models.CharField(max_length=50, blank=True, default="User")
    manage_users_th_email = models.CharField(max_length=50, blank=True, default="Email")
    manage_users_th_permissions = models.CharField(max_length=50, blank=True, default="Permissions")
    manage_users_th_status = models.CharField(max_length=50, blank=True, default="Status")
    manage_users_th_actions = models.CharField(max_length=50, blank=True, default="Actions")
    manage_users_tab_admins = models.CharField(max_length=50, blank=True, default="Administrators")
    manage_users_tab_groups = models.CharField(max_length=50, blank=True, default="Groups")
    manage_users_tab_users  = models.CharField(max_length=50, blank=True, default="Users")

    # Table headers
    manage_users_th_group   = models.CharField(max_length=50, blank=True, default="Group")
    manage_users_th_role    = models.CharField(max_length=50, blank=True, default="Role")

    # Status / Role badges
    manage_users_badge_active   = models.CharField(max_length=50, blank=True, default="Active")
    manage_users_badge_blocked  = models.CharField(max_length=50, blank=True, default="Blocked")
    manage_users_badge_admin    = models.CharField(max_length=50, blank=True, default="Admin")
    manage_users_badge_you      = models.CharField(max_length=20, blank=True, default="You")

    # Common buttons
    manage_users_btn_cancel          = models.CharField(max_length=50, blank=True, default="Cancel")
    manage_users_btn_move            = models.CharField(max_length=50, blank=True, default="Move")
    manage_users_btn_delete          = models.CharField(max_length=50, blank=True, default="Delete")
    manage_users_btn_save_changes    = models.CharField(max_length=50, blank=True, default="Save Changes")
    manage_users_btn_create_group    = models.CharField(max_length=50, blank=True, default="Create Group")
    manage_users_btn_add_user_submit = models.CharField(max_length=50, blank=True, default="Add User")

    # Add User Modal form labels
    manage_users_label_first_name       = models.CharField(max_length=50, blank=True, default="First Name")
    manage_users_label_last_name        = models.CharField(max_length=50, blank=True, default="Last Name")
    manage_users_label_password         = models.CharField(max_length=50, blank=True, default="Password")
    manage_users_label_assign_group     = models.CharField(max_length=50, blank=True, default="Assign to Group")
    manage_users_text_permissions_note  = models.CharField(max_length=200, blank=True, default="Permissions are inherited from the selected group.")
    manage_users_option_no_group        = models.CharField(max_length=50, blank=True, default="\u2014 No Group \u2014")

    # Add/Edit Group Modal form labels
    manage_users_label_group_name       = models.CharField(max_length=50, blank=True, default="Group Name")
    manage_users_label_group_desc       = models.CharField(max_length=50, blank=True, default="Description")
    manage_users_label_permissions      = models.CharField(max_length=100, blank=True, default="Permissions for this Group")
    manage_users_perm_create            = models.CharField(max_length=50, blank=True, default="Create Posts")
    manage_users_perm_edit              = models.CharField(max_length=50, blank=True, default="Edit Posts")
    manage_users_perm_publish           = models.CharField(max_length=50, blank=True, default="Publish Posts")
    manage_users_perm_comments          = models.CharField(max_length=50, blank=True, default="Manage Comments")
    manage_users_placeholder_group_name = models.CharField(max_length=100, blank=True, default="e.g. Writers, Editors")
    manage_users_placeholder_group_desc = models.CharField(max_length=100, blank=True, default="Optional description")

    # Edit / Assign / Delete Group Modal titles & texts
    manage_users_modal_edit_group_title   = models.CharField(max_length=100, blank=True, default="Edit Group")
    manage_users_modal_assign_group_title = models.CharField(max_length=100, blank=True, default="Assign to Group")
    manage_users_text_moving              = models.CharField(max_length=50, blank=True, default="Moving:")
    manage_users_modal_delete_group_title = models.CharField(max_length=100, blank=True, default="Delete Group")
    manage_users_text_delete_confirm      = models.CharField(max_length=200, blank=True, default="Are you sure you want to delete group")
    manage_users_text_delete_warning      = models.CharField(max_length=200, blank=True, default="Members of this group will become ungrouped.")

    # Remove User Confirmation Modal (Dynamic CMS Fields)
    manage_users_modal_remove_user_title   = models.CharField(max_length=100, blank=True, default="Remove Team Member?")
    manage_users_text_remove_user_confirm  = models.CharField(max_length=255, blank=True, default="Are you sure you want to permanently remove this user from the team? This action cannot be undone.")
    manage_users_btn_remove_user_confirm   = models.CharField(max_length=50, blank=True, default="Yes, Delete")

    # Empty states
    manage_users_text_no_groups         = models.CharField(max_length=200, blank=True, default="No permission groups created yet.")
    manage_users_btn_create_first_group = models.CharField(max_length=100, blank=True, default="Create First Group")
    manage_users_text_no_members        = models.CharField(max_length=200, blank=True, default="No members assigned yet.")

    # Email Settings (SMTP) Tab & Section CMS Fields
    manage_users_tab_email              = models.CharField(max_length=60, blank=True, default="Email Settings (SMTP)")
    smtp_settings_heading               = models.CharField(max_length=100, blank=True, default="Company Email Configuration (SMTP)")
    smtp_settings_subtext               = models.CharField(max_length=255, blank=True, default="Configure your company's email server (e.g. Gmail, Outlook, Amazon SES) to send invitation emails to new users.")
    
    # One-Click Google OAuth Card (Dynamic CMS Fields)
    google_card_title                   = models.CharField(max_length=100, blank=True, default="Connect with Google")
    google_card_subtext                 = models.CharField(max_length=255, blank=True, default="Authorize your Gmail account securely with 1-click. No passwords or port setup needed.")
    google_card_badge_text              = models.CharField(max_length=50, blank=True, default="RECOMMENDED")
    google_btn_text                     = models.CharField(max_length=80, blank=True, default="Connect with Google (One Click)")
    google_auth_note                    = models.CharField(max_length=255, blank=True, default="Clicking below opens Google's secure authorization screen to grant email sending permission (gmail.send).")
    
    # Manual SMTP Card (Dynamic CMS Fields)
    manual_smtp_card_title              = models.CharField(max_length=100, blank=True, default="Manual SMTP Setup")
    manual_smtp_card_subtext            = models.CharField(max_length=255, blank=True, default="Use custom SMTP credentials (for custom domain, Outlook, or Amazon SES).")

    smtp_sender_name_label              = models.CharField(max_length=60, blank=True, default="Sender Display Name")
    smtp_sender_name_hint               = models.CharField(max_length=100, blank=True, default="Name shown in receiver's inbox.")
    smtp_sender_email_label             = models.CharField(max_length=60, blank=True, default="Sender Email (SMTP User)")
    smtp_sender_email_hint              = models.CharField(max_length=100, blank=True, default="Your company Gmail / email address.")
    smtp_password_label                 = models.CharField(max_length=60, blank=True, default="SMTP Password / Google App Password")
    smtp_password_hint                  = models.CharField(max_length=255, blank=True, default="For Gmail, use a 16-digit App Password (from Google Account > Security > 2-Step Verification > App Passwords).")
    smtp_host_label                     = models.CharField(max_length=60, blank=True, default="SMTP Host")
    smtp_port_label                     = models.CharField(max_length=60, blank=True, default="SMTP Port")
    smtp_tls_label                      = models.CharField(max_length=60, blank=True, default="Use TLS")
    smtp_save_btn_text                  = models.CharField(max_length=60, blank=True, default="Save Email Settings")
    smtp_instructions_heading           = models.CharField(max_length=100, blank=True, default="Gmail Setup Instructions:")
    smtp_instructions_body              = RichTextField(blank=True, default="<ol><li>Go to your <strong>Google Account</strong> &gt; <strong>Security</strong>.</li><li>Turn on <strong>2-Step Verification</strong> if not already active.</li><li>Search for <strong>\"App passwords\"</strong> in Google settings.</li><li>Create an app named <code>InsightCMS</code> and copy the 16-character code.</li><li>Paste the code in <strong>SMTP Password</strong> above and click Save!</li></ol>", verbose_name="Gmail Setup Instructions Content")

    # Edit User Modal Labels
    manage_users_modal_edit_user_title  = models.CharField(max_length=100, blank=True, default="Edit User Details")
    manage_users_field_first_name       = models.CharField(max_length=60, blank=True, default="First Name")
    manage_users_field_last_name        = models.CharField(max_length=60, blank=True, default="Last Name")
    manage_users_field_email            = models.CharField(max_length=60, blank=True, default="Email Address")
    manage_users_field_role             = models.CharField(max_length=60, blank=True, default="Role")
    manage_users_field_password         = models.CharField(max_length=60, blank=True, default="Reset Password")
    manage_users_option_editor          = models.CharField(max_length=60, blank=True, default="Employee (Company User)")
    manage_users_text_leave_blank       = models.CharField(max_length=100, blank=True, default="Leave blank to keep current")

    # Super Admin Companies Listing (Dynamic CMS Fields)
    dashboard_tab_companies_title       = models.CharField(max_length=100, blank=True, default="Registered Companies", help_text="Tab label for Super Admin companies table")
    dashboard_tab_authors_title         = models.CharField(max_length=100, blank=True, default="All Authors & Team", help_text="Tab label for Super Admin authors table")
    th_company_name_label               = models.CharField(max_length=50, blank=True, default="Company Name")
    th_company_domain_label             = models.CharField(max_length=50, blank=True, default="Domain / Slug")
    th_company_admin_label              = models.CharField(max_length=50, blank=True, default="Company Admin")
    th_company_blogs_label              = models.CharField(max_length=50, blank=True, default="Total Blogs")
    th_company_members_label            = models.CharField(max_length=50, blank=True, default="Members")
    th_company_status_label             = models.CharField(max_length=50, blank=True, default="Status")
    th_company_actions_label            = models.CharField(max_length=50, blank=True, default="Actions")
    no_companies_text                   = models.CharField(max_length=200, blank=True, default="No companies registered yet.")
    btn_remove_company_label            = models.CharField(max_length=50, blank=True, default="Remove")
    modal_remove_company_title          = models.CharField(max_length=100, blank=True, default="Remove Company?")
    modal_remove_company_confirm_text   = models.CharField(max_length=255, blank=True, default="Are you sure you want to permanently remove this company? All associated data will be removed. This action cannot be undone.")
    modal_remove_company_btn_confirm    = models.CharField(max_length=50, blank=True, default="Yes, Delete")
    modal_remove_company_btn_cancel     = models.CharField(max_length=50, blank=True, default="Cancel")
    companies_page_title                = models.CharField(max_length=100, blank=True, default="Companies Management", help_text="Heading for /companies/ page")
    companies_page_subtext              = models.CharField(max_length=255, blank=True, default="Manage all registered client companies, workspaces, and team admins.", help_text="Subtext for /companies/ page")
    companies_stat_total_label          = models.CharField(max_length=50, blank=True, default="Total Companies")
    companies_stat_active_label         = models.CharField(max_length=50, blank=True, default="Active Companies")
    companies_stat_blogs_label          = models.CharField(max_length=50, blank=True, default="Total Blogs")
    companies_stat_members_label        = models.CharField(max_length=50, blank=True, default="Total Members")
    companies_search_placeholder        = models.CharField(max_length=100, blank=True, default="Search company by name or domain...")
    companies_search_button_label       = models.CharField(max_length=50, blank=True, default="Search")
    companies_pagination_showing_text   = models.CharField(max_length=50, blank=True, default="Showing")
    companies_pagination_to_text        = models.CharField(max_length=50, blank=True, default="to")
    companies_pagination_of_text        = models.CharField(max_length=50, blank=True, default="of")
    companies_pagination_companies_text = models.CharField(max_length=50, blank=True, default="companies")
    companies_pagination_prev_text      = models.CharField(max_length=50, blank=True, default="Previous")
    companies_pagination_next_text      = models.CharField(max_length=50, blank=True, default="Next")
    dashboard_view_all_companies_label  = models.CharField(max_length=100, blank=True, default="View All Companies", help_text="Label for View All Companies button on dashboard")

    # Company Detail Page CMS Fields (/companies/<uuid>/)
    detail_back_btn_text                = models.CharField(max_length=60, blank=True, default="Back to Companies", help_text="Back button text on Company Detail page")
    detail_card_info_title              = models.CharField(max_length=80, blank=True, default="Company Information")
    detail_card_contact_title           = models.CharField(max_length=80, blank=True, default="Admin & Contact")
    detail_card_members_title           = models.CharField(max_length=80, blank=True, default="Team Members")
    detail_stat_members_label           = models.CharField(max_length=50, blank=True, default="Members")
    detail_th_domain_label              = models.CharField(max_length=50, blank=True, default="Domain / Slug")
    detail_th_website_name_label        = models.CharField(max_length=50, blank=True, default="Website Name")
    detail_th_website_url_label         = models.CharField(max_length=50, blank=True, default="Website URL")
    detail_th_registered_label          = models.CharField(max_length=50, blank=True, default="Registered On")
    detail_th_status_label              = models.CharField(max_length=50, blank=True, default="Account Status")
    detail_th_approval_label            = models.CharField(max_length=50, blank=True, default="Approval")
    detail_th_admin_name_label          = models.CharField(max_length=50, blank=True, default="Company Admin")
    detail_th_admin_email_label         = models.CharField(max_length=50, blank=True, default="Admin Email")
    detail_th_contact_person_label      = models.CharField(max_length=50, blank=True, default="Contact Person")
    detail_th_contact_email_label       = models.CharField(max_length=50, blank=True, default="Contact Email")
    detail_empty_members_text           = models.CharField(max_length=120, blank=True, default="No members found.")

    # Manage User Settings Placeholder Page CMS Fields
    manage_users_breadcrumb_settings_text = models.CharField(max_length=50, blank=True, default="Settings")
    manage_users_breadcrumb_active_text   = models.CharField(max_length=50, blank=True, default="Manage User Settings")
    manage_users_placeholder_title        = models.CharField(max_length=100, blank=True, default="Manage User Settings")
    manage_users_placeholder_desc         = models.TextField(blank=True, default="This settings module is currently in development. You will soon be able to manage user invitations, fine-grained access levels, and workspace roles directly from here.")
    manage_users_btn_comments_settings    = models.CharField(max_length=60, blank=True, default="Go to Comments Settings")
    manage_users_btn_view_team            = models.CharField(max_length=60, blank=True, default="View Team Members")

    # Website Integration Page CMS Fields (Comprehensive Dynamic Customization)
    integration_page_title = models.CharField(max_length=100, blank=True, default="Website Integration Guide")
    integration_page_subtext = models.CharField(max_length=255, blank=True, default="Step-by-step instructions for integrating blogs on any website.")
    
    # Step 1
    integration_step1_badge = models.CharField(max_length=30, blank=True, default="Step 1")
    integration_step1_title = models.CharField(max_length=100, blank=True, default="Your Live RSS Feed Endpoint")
    integration_step1_desc_prefix = models.CharField(max_length=150, blank=True, default="All blogs published under")
    integration_step1_desc_suffix = models.CharField(max_length=150, blank=True, default="are live at this RSS XML endpoint:")
    integration_step1_copy_btn_text = models.CharField(max_length=50, blank=True, default="Copy URL")
    integration_step1_website_active_text = models.CharField(max_length=150, blank=True, default="Using your website URL:")
    integration_step1_website_fallback_text = models.CharField(max_length=255, blank=True, default="Showing local URL. Set your website URL in Settings to show your real domain here.")

    # Step 2
    integration_step2_badge = models.CharField(max_length=30, blank=True, default="Step 2")
    integration_step2_title = models.CharField(max_length=100, blank=True, default="Embed Blogs on Your Website")
    integration_step2_subtext = models.CharField(max_length=200, blank=True, default="Pick your framework — copy the snippet and paste it in your project.")

    # Step 3
    integration_step3_badge = models.CharField(max_length=30, blank=True, default="Step 3")
    integration_step3_title = models.CharField(max_length=100, blank=True, default="How It Works")
    integration_step3_point1 = models.CharField(max_length=255, blank=True, default="Copy the RSS Feed URL from Step 1.")
    integration_step3_point2 = models.CharField(max_length=255, blank=True, default="Pick your framework tab in Step 2, copy the snippet, and paste it in your project.")
    integration_step3_point3 = models.CharField(max_length=255, blank=True, default="Whenever you publish or update a blog here, it instantly syncs to your website!")

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("settings_page_title"),
            FieldPanel("settings_page_subtext"),
            FieldPanel("settings_tab_1_title"),
            FieldPanel("settings_tab_4_title"),
            FieldPanel("settings_tab_team_title"),
            FieldPanel("settings_tab_comments_title"),
        ], heading="Page Header & Tabs"),
        MultiFieldPanel([
            FieldPanel("comments_setting_heading"),
            FieldPanel("comments_setting_subtext"),
            FieldPanel("comments_setting_btn_text"),
            FieldPanel("comments_gen_heading"),
            FieldPanel("comments_gen_subtext"),
            FieldPanel("comments_enable_label"),
            FieldPanel("comments_enable_desc"),
            FieldPanel("comments_replies_label"),
            FieldPanel("comments_replies_desc"),
            FieldPanel("comments_per_page_label"),
            FieldPanel("comments_per_page_desc"),
            FieldPanel("comments_mod_heading"),
            FieldPanel("comments_mod_subtext"),
            FieldPanel("comments_review_all_label"),
            FieldPanel("comments_review_all_desc"),
            FieldPanel("comments_under_review_label"),
            FieldPanel("comments_under_review_ph"),
            FieldPanel("comments_fields_heading"),
            FieldPanel("comments_fields_subtext"),
            FieldPanel("comments_name_req_label"),
            FieldPanel("comments_name_req_desc"),
            FieldPanel("comments_email_mode_label"),
            FieldPanel("comments_email_mode_desc"),
        ], heading="Blog Comments Configuration (General, Moderation, Form Fields)"),
        MultiFieldPanel([
            FieldPanel("manage_users_page_title"),
            FieldPanel("manage_users_page_subtext"),
            # Tabs
            FieldPanel("manage_users_tab_admins"),
            FieldPanel("manage_users_tab_groups"),
            FieldPanel("manage_users_tab_users"),
            # Header Buttons
            FieldPanel("manage_users_btn_add_text"),
            FieldPanel("manage_users_btn_add_group"),
            # Table Headers
            FieldPanel("manage_users_th_user"),
            FieldPanel("manage_users_th_email"),
            FieldPanel("manage_users_th_group"),
            FieldPanel("manage_users_th_role"),
            FieldPanel("manage_users_th_permissions"),
            FieldPanel("manage_users_th_status"),
            FieldPanel("manage_users_th_actions"),
            # Status Badges
            FieldPanel("manage_users_badge_active"),
            FieldPanel("manage_users_badge_blocked"),
            FieldPanel("manage_users_badge_admin"),
            FieldPanel("manage_users_badge_you"),
            # Common Buttons
            FieldPanel("manage_users_btn_cancel"),
            FieldPanel("manage_users_btn_move"),
            FieldPanel("manage_users_btn_delete"),
            FieldPanel("manage_users_btn_save_changes"),
            FieldPanel("manage_users_btn_create_group"),
            FieldPanel("manage_users_btn_add_user_submit"),
            # Add User Modal
            FieldPanel("manage_users_modal_add_user_title"),
            FieldPanel("manage_users_label_first_name"),
            FieldPanel("manage_users_label_last_name"),
            FieldPanel("manage_users_label_password"),
            FieldPanel("manage_users_label_assign_group"),
            FieldPanel("manage_users_option_no_group"),
            FieldPanel("manage_users_text_permissions_note"),
            # Add Group Modal
            FieldPanel("manage_users_modal_add_group_title"),
            FieldPanel("manage_users_label_group_name"),
            FieldPanel("manage_users_label_group_desc"),
            FieldPanel("manage_users_label_permissions"),
            FieldPanel("manage_users_perm_create"),
            FieldPanel("manage_users_perm_edit"),
            FieldPanel("manage_users_perm_publish"),
            FieldPanel("manage_users_perm_comments"),
            FieldPanel("manage_users_placeholder_group_name"),
            FieldPanel("manage_users_placeholder_group_desc"),
            # Edit Group Modal
            FieldPanel("manage_users_modal_edit_group_title"),
            FieldPanel("manage_users_btn_save_changes"),
            # Assign Group Modal
            FieldPanel("manage_users_modal_assign_group_title"),
            FieldPanel("manage_users_text_moving"),
            # Delete Group Modal
            FieldPanel("manage_users_modal_delete_group_title"),
            FieldPanel("manage_users_text_delete_confirm"),
            FieldPanel("manage_users_text_delete_warning"),
            # Remove User Modal
            FieldPanel("manage_users_modal_remove_user_title"),
            FieldPanel("manage_users_text_remove_user_confirm"),
            FieldPanel("manage_users_btn_remove_user_confirm"),
            # Empty States
            FieldPanel("manage_users_text_no_groups"),
            FieldPanel("manage_users_btn_create_first_group"),
            FieldPanel("manage_users_text_no_members"),
            FieldPanel("manage_users_card_heading"),
            # Email Settings (SMTP & Google OAuth) Section
            FieldPanel("manage_users_tab_email"),
            FieldPanel("smtp_settings_heading"),
            FieldPanel("smtp_settings_subtext"),
            # Google One-Click Card
            FieldPanel("google_card_title"),
            FieldPanel("google_card_subtext"),
            FieldPanel("google_card_badge_text"),
            FieldPanel("google_btn_text"),
            FieldPanel("google_auth_note"),
            # Manual SMTP Card
            FieldPanel("manual_smtp_card_title"),
            FieldPanel("manual_smtp_card_subtext"),
            FieldPanel("smtp_sender_name_label"),
            FieldPanel("smtp_sender_name_hint"),
            FieldPanel("smtp_sender_email_label"),
            FieldPanel("smtp_sender_email_hint"),
            FieldPanel("smtp_password_label"),
            FieldPanel("smtp_password_hint"),
            FieldPanel("smtp_host_label"),
            FieldPanel("smtp_port_label"),
            FieldPanel("smtp_tls_label"),
            FieldPanel("smtp_save_btn_text"),
            FieldPanel("smtp_instructions_heading"),
            FieldPanel("smtp_instructions_body"),
            # Edit User Modal
            FieldPanel("manage_users_modal_edit_user_title"),
            FieldPanel("manage_users_field_first_name"),
            FieldPanel("manage_users_field_last_name"),
            FieldPanel("manage_users_field_email"),
            FieldPanel("manage_users_field_role"),
            FieldPanel("manage_users_field_password"),
            FieldPanel("manage_users_option_editor"),
            FieldPanel("manage_users_text_leave_blank"),
        ], heading="Manage User Settings Configuration"),
        MultiFieldPanel([
            FieldPanel("settings_profile_heading"),
            FieldPanel("settings_profile_subtext"),
            FieldPanel("settings_profile_avatar_btn_text"),
            FieldPanel("settings_profile_fname_label"),
            FieldPanel("settings_profile_lname_label"),
            FieldPanel("settings_profile_email_label"),
            FieldPanel("settings_profile_email_hint"),
            FieldPanel("settings_profile_role_label"),
            FieldPanel("settings_profile_btn_text"),
        ], heading="Profile Section"),
        MultiFieldPanel([
            FieldPanel("settings_security_heading"),
            FieldPanel("settings_security_subtext"),
            FieldPanel("settings_sec_curr_pass_label"),
            FieldPanel("settings_sec_curr_pass_ph"),
            FieldPanel("settings_sec_new_pass_label"),
            FieldPanel("settings_sec_new_pass_ph"),
            FieldPanel("settings_sec_conf_pass_label"),
            FieldPanel("settings_sec_conf_pass_ph"),
            FieldPanel("settings_security_badge_text"),
            FieldPanel("settings_security_btn_text"),
            FieldPanel("settings_session_title"),
            FieldPanel("settings_session_desc"),
            FieldPanel("settings_sec_signout_btn_text"),
        ], heading="Security Section"),
        MultiFieldPanel([
            FieldPanel("team_add_heading"),
            FieldPanel("team_add_subtext"),
            FieldPanel("team_email_label"),
            FieldPanel("team_email_ph"),
            FieldPanel("team_password_label"),
            FieldPanel("team_password_ph"),
            FieldPanel("team_fname_label"),
            FieldPanel("team_fname_ph"),
            FieldPanel("team_lname_label"),
            FieldPanel("team_lname_ph"),
            FieldPanel("team_add_btn_text"),
            FieldPanel("team_list_heading"),
            FieldPanel("team_list_subtext"),
            FieldPanel("team_th_user"),
            FieldPanel("team_th_role"),
            FieldPanel("team_th_email"),
            FieldPanel("team_th_status"),
            FieldPanel("team_status_active_text"),
            FieldPanel("team_empty_text"),
        ], heading="Team Members Section"),
        MultiFieldPanel([
            FieldPanel("integration_page_title"),
            FieldPanel("integration_page_subtext"),
            FieldPanel("integration_step1_badge"),
            FieldPanel("integration_step1_title"),
            FieldPanel("integration_step1_desc_prefix"),
            FieldPanel("integration_step1_desc_suffix"),
            FieldPanel("integration_step1_copy_btn_text"),
            FieldPanel("integration_step1_website_active_text"),
            FieldPanel("integration_step1_website_fallback_text"),
            FieldPanel("integration_step2_badge"),
            FieldPanel("integration_step2_title"),
            FieldPanel("integration_step2_subtext"),
            FieldPanel("integration_step3_badge"),
            FieldPanel("integration_step3_title"),
            FieldPanel("integration_step3_point1"),
            FieldPanel("integration_step3_point2"),
            FieldPanel("integration_step3_point3"),
        ], heading="Website Integration Guide Settings"),
        MultiFieldPanel([
            FieldPanel("dashboard_tab_companies_title"),
            FieldPanel("dashboard_tab_authors_title"),
            FieldPanel("th_company_name_label"),
            FieldPanel("th_company_domain_label"),
            FieldPanel("th_company_admin_label"),
            FieldPanel("th_company_blogs_label"),
            FieldPanel("th_company_members_label"),
            FieldPanel("th_company_status_label"),
            FieldPanel("th_company_actions_label"),
            FieldPanel("no_companies_text"),
            FieldPanel("btn_remove_company_label"),
            FieldPanel("modal_remove_company_title"),
            FieldPanel("modal_remove_company_confirm_text"),
            FieldPanel("modal_remove_company_btn_confirm"),
            FieldPanel("modal_remove_company_btn_cancel"),
            FieldPanel("companies_page_title"),
            FieldPanel("companies_page_subtext"),
            FieldPanel("companies_stat_total_label"),
            FieldPanel("companies_stat_active_label"),
            FieldPanel("companies_stat_blogs_label"),
            FieldPanel("companies_stat_members_label"),
            FieldPanel("companies_search_placeholder"),
            FieldPanel("companies_search_button_label"),
            FieldPanel("companies_pagination_showing_text"),
            FieldPanel("companies_pagination_to_text"),
            FieldPanel("companies_pagination_of_text"),
            FieldPanel("companies_pagination_companies_text"),
            FieldPanel("companies_pagination_prev_text"),
            FieldPanel("companies_pagination_next_text"),
            FieldPanel("dashboard_view_all_companies_label"),
            FieldPanel("detail_back_btn_text"),
            FieldPanel("detail_card_info_title"),
            FieldPanel("detail_card_contact_title"),
            FieldPanel("detail_card_members_title"),
            FieldPanel("detail_stat_members_label"),
            FieldPanel("detail_th_domain_label"),
            FieldPanel("detail_th_website_name_label"),
            FieldPanel("detail_th_website_url_label"),
            FieldPanel("detail_th_registered_label"),
            FieldPanel("detail_th_status_label"),
            FieldPanel("detail_th_approval_label"),
            FieldPanel("detail_th_admin_name_label"),
            FieldPanel("detail_th_admin_email_label"),
            FieldPanel("detail_th_contact_person_label"),
            FieldPanel("detail_th_contact_email_label"),
            FieldPanel("detail_empty_members_text"),
            FieldPanel("manage_users_breadcrumb_settings_text"),
            FieldPanel("manage_users_breadcrumb_active_text"),
            FieldPanel("manage_users_placeholder_title"),
            FieldPanel("manage_users_placeholder_desc"),
            FieldPanel("manage_users_btn_comments_settings"),
            FieldPanel("manage_users_btn_view_team"),
        ], heading="Super Admin Companies Listing & Detail Settings"),
    ]

    parent_page_types = ["wagtailcore.Page", "companies.CompanyHomePage"]
    subpage_types = []
    template = "accounts/settings.html"

    def serve(self, request):
        from django.contrib.auth import get_user_model
        from django.contrib import messages
        from Apps.companies.models import CompanyMembership

        if not request.user.is_authenticated:
            login_page = LoginPage.objects.live().first()
            return redirect(login_page.url if login_page else '/login/')

        User = get_user_model()

        membership = CompanyMembership.objects.filter(user=request.user).select_related('company').first()
        company = membership.company if membership else None

        if request.method == "POST" and request.POST.get("action_type") == "update_comments_setting":
            if not company:
                messages.error(request, "No company found for your account.")
                return redirect(request.path + "#comments")

            if request.user.role != User.Role.COMPANY_ADMIN and not request.user.is_superuser:
                messages.error(request, "Only Company Admin can update global comment settings.")
                return redirect(request.path + "#comments")

            allow_comments_val = request.POST.get("allow_comments") == "on"
            company.allow_comments = allow_comments_val
            company.save()
            messages.success(request, f"Global comment settings updated! Comments are now {'ENABLED' if allow_comments_val else 'DISABLED'} across all blogs.")
            return redirect(request.path + "#comments")

        if request.method == "POST" and request.POST.get("action_type") == "add_team_member":
            if not company:
                messages.error(request, "No company found for your account.")
                return redirect(request.path + "#team")

            if request.user.role != User.Role.COMPANY_ADMIN and not request.user.is_superuser:
                messages.error(request, "You don't have permission to add team members.")
                return redirect(request.path + "#team")

            email = request.POST.get("member_email", "").strip().lower()
            password = request.POST.get("member_password", "")
            first_name = request.POST.get("member_first_name", "").strip()
            last_name = request.POST.get("member_last_name", "").strip()

            if not email or not password:
                messages.error(request, "Email and password are required.")
                return redirect(request.path + "#team")

            if User.objects.filter(email=email).exists():
                messages.error(request, "A user with this email already exists.")
                return redirect(request.path + "#team")

            new_user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=User.Role.COMPANY_USER,
                is_staff=True,
                company_name=company.name if hasattr(company, 'name') else "",
            )

            CompanyMembership.objects.create(
                user=new_user,
                company=company,
                role=CompanyMembership.Role.EDITOR
            )

            messages.success(request, f"Team member {email} added successfully.")
            return redirect(request.path + "#team")

        team_members = []
        if company:
            team_members = CompanyMembership.objects.filter(company=company).select_related('user')

        context = self.get_context(request)
        context.update({
            'page': self,
            'user': request.user,
            'company': company,
            'team_members': team_members,
        })
        return render(request, self.template, context)

    class Meta:
        verbose_name = "Settings Page"


class UserNotification(BaseModel):
    """Notification model for user alerts (Approve/Reject blog notifications)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    notification_type = models.CharField(max_length=50, default='info') # 'approved', 'rejected', 'info'

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.email}: {self.title}"