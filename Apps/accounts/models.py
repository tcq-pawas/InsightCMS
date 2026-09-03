from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from Apps.common.models import BaseModel
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import StreamField
from django.shortcuts import redirect, render
from django.contrib.auth import login as auth_login

# Import our custom dashboard blocks from blocks.py
from Apps.accounts.blocks import (
    SidebarLinkBlock,
    StatCardBlock,
    TopbarBlock,
    UpgradeBannerBlock,
    SidebarUpgradeCardBlock,
    DashboardFooterBlock,
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
        MANAGER = 'manager', _('Manager')

    username = None
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
            user = form.get_user()
            auth_login(request, user)
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
            return redirect("/dashboard/")

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

    recent_posts_heading = models.CharField(max_length=150, blank=True, default="Recent Posts")
    recent_posts_subtext = models.CharField(max_length=255, blank=True, default="Manage your latest published and draft articles")
    view_all_posts_text = models.CharField(max_length=50, blank=True, default="View All")
    view_all_posts_url = models.CharField(max_length=255, blank=True, default="/cms/pages/")

    # Recent Posts Table Column Headers (Fully Dynamic)
    th_post_title = models.CharField(max_length=50, blank=True, default="POST TITLE")
    th_category = models.CharField(max_length=50, blank=True, default="CATEGORY")
    th_status = models.CharField(max_length=50, blank=True, default="STATUS")
    th_views = models.CharField(max_length=50, blank=True, default="VIEWS")
    th_date = models.CharField(max_length=50, blank=True, default="DATE")
    th_actions = models.CharField(max_length=50, blank=True, default="ACTIONS")

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

    # 10. Settings Page Content (Fully Dynamic Wagtail)
    settings_page_title = models.CharField(max_length=100, blank=True, default="Settings")
    settings_page_subtext = models.CharField(max_length=255, blank=True, default="Manage your account preferences, workspace, and security settings.")

    # Settings Dynamic Tab Labels
    settings_tab_1_title = models.CharField(max_length=50, blank=True, default="Profile")
    settings_tab_2_title = models.CharField(max_length=50, blank=True, default="Workspace")
    settings_tab_3_title = models.CharField(max_length=50, blank=True, default="Notifications")
    settings_tab_4_title = models.CharField(max_length=50, blank=True, default="Security")

    # Settings Profile Section
    settings_profile_heading = models.CharField(max_length=100, blank=True, default="Profile Information")
    settings_profile_subtext = models.CharField(max_length=255, blank=True, default="Update your personal details and public profile presence.")
    settings_profile_btn_text = models.CharField(max_length=50, blank=True, default="Save Changes")

    # Settings Workspace Section
    settings_workspace_heading = models.CharField(max_length=100, blank=True, default="Workspace Details")
    settings_workspace_subtext = models.CharField(max_length=255, blank=True, default="Configure your blog workspace, public name, and publishing preferences.")
    settings_workspace_domain = models.CharField(max_length=100, blank=True, default="insightcms.local")
    settings_workspace_btn_text = models.CharField(max_length=50, blank=True, default="Save Workspace")

    # Settings Notifications Section
    settings_notif_heading = models.CharField(max_length=100, blank=True, default="Notification Preferences")
    settings_notif_subtext = models.CharField(max_length=255, blank=True, default="Choose when and how you want to be notified about blog activities.")
    settings_notif_1_title = models.CharField(max_length=150, blank=True, default="New Comments & Reader Interactions")
    settings_notif_1_desc = models.CharField(max_length=255, blank=True, default="Get notified immediately whenever a reader leaves a comment on your posts.")
    settings_notif_2_title = models.CharField(max_length=150, blank=True, default="Weekly Analytics Digest")
    settings_notif_2_desc = models.CharField(max_length=255, blank=True, default="Receive a weekly summary of your blog's visitors, top posts, and subscriber growth.")
    settings_notif_3_title = models.CharField(max_length=150, blank=True, default="System & Security Alerts")
    settings_notif_3_desc = models.CharField(max_length=255, blank=True, default="Important updates about your account security and CMS updates.")
    settings_notif_btn_text = models.CharField(max_length=50, blank=True, default="Save Preferences")

    # Settings Security Section
    settings_security_heading = models.CharField(max_length=100, blank=True, default="Security & Authentication")
    settings_security_subtext = models.CharField(max_length=255, blank=True, default="Manage your password, login security, and active sessions.")
    settings_security_badge_text = models.CharField(max_length=50, blank=True, default="Account Protected")
    settings_security_btn_text = models.CharField(max_length=50, blank=True, default="Update Password")
    settings_session_title = models.CharField(max_length=100, blank=True, default="Active Session")
    settings_session_desc = models.CharField(max_length=255, blank=True, default="Currently signed in from this browser.")

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("brand_name"),
            FieldPanel("welcome_heading"),
            FieldPanel("welcome_subtext"),
            FieldPanel("new_post_button_text"),
            FieldPanel("new_post_button_url"),
        ], heading="1. Header & Brand"),

        FieldPanel("sidebar_links", heading="2. Dynamic Sidebar Links"),

        MultiFieldPanel([
            FieldPanel("search_placeholder"),
            FieldPanel("search_shortcut"),
            FieldPanel("notification_count"),
        ], heading="3. Topbar Header Settings"),

        MultiFieldPanel([
            FieldPanel("stat1_label"),
            FieldPanel("stat1_value"),
            FieldPanel("stat1_growth"),
            FieldPanel("stat2_label"),
            FieldPanel("stat2_value"),
            FieldPanel("stat2_growth"),
            FieldPanel("stat3_label"),
            FieldPanel("stat3_value"),
            FieldPanel("stat3_growth"),
            FieldPanel("stat4_label"),
            FieldPanel("stat4_value"),
            FieldPanel("stat4_growth"),
            FieldPanel("stat5_label"),
            FieldPanel("stat5_value"),
            FieldPanel("stat5_growth"),
            FieldPanel("stat_caption"),
        ], heading="4. Top 5 Stat Cards (Labels, Values & Growth)"),

        MultiFieldPanel([
            FieldPanel("views_chart_heading"),
            FieldPanel("views_chart_subtext"),
            FieldPanel("views_filter_1"),
            FieldPanel("views_filter_2"),
            FieldPanel("views_filter_3"),
        ], heading="5. Views Overview"),

        MultiFieldPanel([
            FieldPanel("recent_posts_heading"),
            FieldPanel("recent_posts_subtext"),
            FieldPanel("view_all_posts_text"),
            FieldPanel("view_all_posts_url"),
            FieldPanel("th_post_title"),
            FieldPanel("th_category"),
            FieldPanel("th_status"),
            FieldPanel("th_views"),
            FieldPanel("th_date"),
            FieldPanel("th_actions"),
        ], heading="6. Recent Posts & Table Headers"),

        MultiFieldPanel([
            FieldPanel("audience_heading"),
            FieldPanel("audience_subtext"),
            FieldPanel("countries_heading"),
            FieldPanel("country_1_name"),
            FieldPanel("country_1_pct"),
            FieldPanel("country_2_name"),
            FieldPanel("country_2_pct"),
            FieldPanel("country_3_name"),
            FieldPanel("country_3_pct"),
            FieldPanel("country_4_name"),
            FieldPanel("country_4_pct"),
            FieldPanel("country_5_name"),
            FieldPanel("country_5_pct"),
            FieldPanel("traffic_heading"),
            FieldPanel("traffic_legend_1"),
            FieldPanel("traffic_legend_2"),
            FieldPanel("device_heading"),
            FieldPanel("device_legend_1"),
            FieldPanel("device_legend_2"),
        ], heading="7. Audience Overview"),


        MultiFieldPanel([
            FieldPanel("comments_heading"),
            FieldPanel("comments_subtext"),
            FieldPanel("view_all_comments_text"),
            FieldPanel("view_all_comments_url"),
            FieldPanel("comment_1_author"),
            FieldPanel("comment_1_time"),
            FieldPanel("comment_1_text"),
            FieldPanel("comment_1_post"),
            FieldPanel("comment_2_author"),
            FieldPanel("comment_2_time"),
            FieldPanel("comment_2_text"),
            FieldPanel("comment_2_post"),
            FieldPanel("comment_3_author"),
            FieldPanel("comment_3_time"),
            FieldPanel("comment_3_text"),
            FieldPanel("comment_3_post"),
        ], heading="9. Recent Comments"),



        MultiFieldPanel([
            FieldPanel("show_upgrade_banner"),
            FieldPanel("upgrade_banner_title"),
            FieldPanel("upgrade_banner_text"),
            FieldPanel("upgrade_banner_button_text"),
            FieldPanel("upgrade_banner_button_url"),
        ], heading="11. Bottom Upgrade Banner"),

        MultiFieldPanel([
            FieldPanel("sidebar_upgrade_title"),
            FieldPanel("sidebar_upgrade_text"),
            FieldPanel("sidebar_upgrade_button_text"),
        ], heading="12. Sidebar Upgrade Card"),

        MultiFieldPanel([
            FieldPanel("footer_tagline"),
            FieldPanel("footer_facebook_url"),
            FieldPanel("footer_twitter_url"),
            FieldPanel("footer_instagram_url"),
            FieldPanel("footer_linkedin_url"),

            # Column 1
            FieldPanel("footer_col1_heading"),
            FieldPanel("footer_col1_link1_text"),
            FieldPanel("footer_col1_link1_url"),
            FieldPanel("footer_col1_link2_text"),
            FieldPanel("footer_col1_link2_url"),
            FieldPanel("footer_col1_link3_text"),
            FieldPanel("footer_col1_link3_url"),
            FieldPanel("footer_col1_link4_text"),
            FieldPanel("footer_col1_link4_url"),

            # Column 2
            FieldPanel("footer_col2_heading"),
            FieldPanel("footer_col2_link1_text"),
            FieldPanel("footer_col2_link1_url"),
            FieldPanel("footer_col2_link2_text"),
            FieldPanel("footer_col2_link2_url"),
            FieldPanel("footer_col2_link3_text"),
            FieldPanel("footer_col2_link3_url"),
            FieldPanel("footer_col2_link4_text"),
            FieldPanel("footer_col2_link4_url"),

            # Column 3
            FieldPanel("footer_col3_heading"),
            FieldPanel("footer_col3_link1_text"),
            FieldPanel("footer_col3_link1_url"),
            FieldPanel("footer_col3_link2_text"),
            FieldPanel("footer_col3_link2_url"),
            FieldPanel("footer_col3_link3_text"),
            FieldPanel("footer_col3_link3_url"),
            FieldPanel("footer_col3_link4_text"),
            FieldPanel("footer_col3_link4_url"),

            # Newsletter
            FieldPanel("newsletter_heading"),
            FieldPanel("newsletter_subtext"),
            FieldPanel("newsletter_placeholder"),
        ], heading="13. Footer Content, Columns & Social Links"),

        MultiFieldPanel([
            FieldPanel("copyright_text"),
            FieldPanel("privacy_policy_text"),
            FieldPanel("privacy_policy_url"),
            FieldPanel("terms_service_text"),
            FieldPanel("terms_service_url"),
        ], heading="14. Footer Bottom & Legal Links"),

        MultiFieldPanel([
            FieldPanel("settings_page_title"),
            FieldPanel("settings_page_subtext"),
            FieldPanel("settings_tab_1_title"),
            FieldPanel("settings_tab_2_title"),
            FieldPanel("settings_tab_3_title"),
            FieldPanel("settings_tab_4_title"),
            FieldPanel("settings_profile_heading"),
            FieldPanel("settings_profile_subtext"),
            FieldPanel("settings_profile_btn_text"),
            FieldPanel("settings_workspace_heading"),
            FieldPanel("settings_workspace_subtext"),
            FieldPanel("settings_workspace_domain"),
            FieldPanel("settings_workspace_btn_text"),
            FieldPanel("settings_notif_heading"),
            FieldPanel("settings_notif_subtext"),
            FieldPanel("settings_notif_1_title"),
            FieldPanel("settings_notif_1_desc"),
            FieldPanel("settings_notif_2_title"),
            FieldPanel("settings_notif_2_desc"),
            FieldPanel("settings_notif_3_title"),
            FieldPanel("settings_notif_3_desc"),
            FieldPanel("settings_notif_btn_text"),
            FieldPanel("settings_security_heading"),
            FieldPanel("settings_security_subtext"),
            FieldPanel("settings_security_badge_text"),
            FieldPanel("settings_security_btn_text"),
            FieldPanel("settings_session_title"),
            FieldPanel("settings_session_desc"),
        ], heading="15. Settings Page (Dynamic)"),
    ]

    parent_page_types = ["wagtailcore.Page", "companies.CompanyHomePage"]
    subpage_types = []
    template = "accounts/dashboard.html"

    def serve(self, request):
        if not request.user.is_authenticated:
            return redirect("/accounts/login/")
        
        from Apps.blogs.models import BlogPage
        blogs = BlogPage.objects.all().order_by('-latest_revision_created_at')[:5]

        context = self.get_context(request)
        context.update({
            'page': self,
            'user': request.user,
            'recent_blogs': blogs,
        })
        return render(request, self.template, context)

    class Meta:
        verbose_name = "User Dashboard Page"