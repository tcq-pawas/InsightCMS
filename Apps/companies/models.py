import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from Apps.common.models import BaseModel
from Apps.common.helpers import generate_api_key
from Apps.companies.blocks import COMPANY_HOME_PAGE_BLOCKS, NAVBAR_BLOCKS
from Apps.companies.forms import CompanyScopedPageForm
from django.conf import settings

# ---------------------------------------------------------------------------
# Company (original model — must stay here, admin.py imports it from here)
# ---------------------------------------------------------------------------
class Company(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_name   = models.CharField(max_length=255, verbose_name="Company Name")
    website_name   = models.CharField(max_length=255, verbose_name="Website Name")
    website_url    = models.URLField(max_length=500, verbose_name="Website URL")
    logo           = models.ImageField(upload_to="company_logos/", blank=True, null=True, verbose_name="Logo")
    email          = models.EmailField(verbose_name="Email")
    contact_person = models.CharField(max_length=255, verbose_name="Contact Person")
    status         = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
        verbose_name="Status",
    )
    api_key        = models.CharField(max_length=64, unique=True, editable=False, verbose_name="API Key")
    domain         = models.CharField(max_length=255, blank=True, null=True, verbose_name="Domain")
    slug           = models.SlugField(max_length=255, unique=True, blank=True, null=True, verbose_name="Slug")
    created_at     = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ["-created_at"]

    def __str__(self):
        return self.company_name

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f"{self.user.email} - {self.company.company_name}"

class CompanyMembership(BaseModel):
    """Connects users to a company with role scoping (manager, editor)."""

    class Role(models.TextChoices):
        MANAGER = 'manager', _('Manager')
        EDITOR  = 'editor',  _('Editor')

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name=_('Company')
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='company_memberships',
        verbose_name=_('User')
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EDITOR,
        verbose_name=_('Role')
    )

    class Meta:
        verbose_name = _('Company Membership')
        verbose_name_plural = _('Company Memberships')
        unique_together = ('company', 'user')

    def __str__(self):
        return f"{self.user.email} - {self.company.company_name} ({self.get_role_display()})"



# ---------------------------------------------------------------------------
# CompanyHomePage (Wagtail page — public website for one company)
# ---------------------------------------------------------------------------
class CompanyHomePage(Page):
    """
    The public, one-page marketing site for a single company.
 
    Content is entirely StreamField-driven so editors can add, remove,
    and reorder sections (hero, about, services, testimonials, blog
    preview, contact, footer) without touching code.
    """
 
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        related_name="home_pages",
        null=True,
        blank=True,
        help_text="The company this website belongs to. Drives data "
                   "isolation for the blog preview section.",
    )
    
    brand_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Brand name shown in the navbar/footer (e.g. 'BlogPro').",
    )

    logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Company logo shown in the header and dashboard card.",
    )
    
    navbar = StreamField(
        NAVBAR_BLOCKS,
        blank=True,
        use_json_field=True,
        max_num=1,
        help_text="Configure the site navigation bar.",
    )

    body = StreamField(
        COMPANY_HOME_PAGE_BLOCKS,
        blank=True,
        use_json_field=True,
        help_text="Build the page by adding, editing, and reordering "
                   "sections below.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("brand_name"),
        FieldPanel("logo"),
        FieldPanel("navbar"),
        FieldPanel("body"),
    ]
    base_form_class = CompanyScopedPageForm
 
    # A CompanyHomePage is typically the root of that company's Wagtail
    # Site, with a BlogIndexPage (from the `blogs` app) living under it.
    parent_page_types = ["wagtailcore.Page"]
    subpage_types = [
        "blogs.BlogIndexPage", 
        "companies.SimpleContentPage",
        "accounts.LoginPage",
        "accounts.RegisterPage",
        "companies.CompanyBlogPostsPage",
    ]
 
    template = "companies/company_home_page.html"
 
    class Meta:
        verbose_name = "Company Home Page"


class SimpleContentPage(Page):
    """
    Generic page for static content like Privacy Policy, Terms of
    Service, About Us, etc. — a heading + rich text body.
    """
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]

    parent_page_types = ["companies.CompanyHomePage", "wagtailcore.Page"]
    subpage_types = []

    template = "companies/simple_content_page.html"

    class Meta:
        verbose_name = "Simple Content Page"
        

class CompanyBlogPostsPage(Page):

    page_heading = models.CharField(max_length=100, blank=True, default="Blog Posts")
    page_subtext = models.CharField(max_length=200, blank=True, default="Manage all blog posts across your workspace")
    create_button_text = models.CharField(max_length=50, blank=True, default="Create Blog Post")

    col_title_label = models.CharField(max_length=50, blank=True, default="Title")
    col_status_label = models.CharField(max_length=50, blank=True, default="Status")
    col_author_label = models.CharField(max_length=50, blank=True, default="Author")
    col_updated_label = models.CharField(max_length=50, blank=True, default="Last Updated")

    empty_state_text = models.CharField(max_length=150, blank=True, default="No blog posts yet.")
    empty_state_link_text = models.CharField(max_length=50, blank=True, default="Create your first one")

    # Create & Edit Blog Form Labels & Placeholders
    create_heading = models.CharField(max_length=100, blank=True, default="Create Blog Post")
    create_subtext = models.CharField(max_length=200, blank=True, default="Write and publish a new article to your blog")
    edit_heading = models.CharField(max_length=100, blank=True, default="Edit Blog Post")
    edit_subtext_prefix = models.CharField(max_length=100, blank=True, default="Update content and settings for")
    draft_button_text = models.CharField(max_length=50, blank=True, default="Save as Draft")
    publish_button_text = models.CharField(max_length=50, blank=True, default="Publish Post")
    update_button_text = models.CharField(max_length=50, blank=True, default="Update & Publish")
    back_button_text = models.CharField(max_length=50, blank=True, default="Back to Blog Posts")

    # Inner Form Field Labels & Placeholders
    field_title_label = models.CharField(max_length=100, blank=True, default="Blog Title")
    field_title_placeholder = models.CharField(max_length=200, blank=True, default="e.g. 10 Tips for Better Web Performance")
    field_category_label = models.CharField(max_length=100, blank=True, default="Category")
    field_category_placeholder = models.CharField(max_length=100, blank=True, default="Select Category")
    field_featured_image_label = models.CharField(max_length=100, blank=True, default="Featured Image")
    field_short_desc_label = models.CharField(max_length=100, blank=True, default="Short Description / Subtitle")
    field_short_desc_placeholder = models.CharField(max_length=200, blank=True, default="Brief summary of your article...")
    field_body_label = models.CharField(max_length=100, blank=True, default="Content Body")
    field_body_placeholder = models.CharField(max_length=200, blank=True, default="Write your full blog post here...")

    content_panels = Page.content_panels + [
        FieldPanel("page_heading"),
        FieldPanel("page_subtext"),
        FieldPanel("create_button_text"),
        FieldPanel("col_title_label"),
        FieldPanel("col_status_label"),
        FieldPanel("col_author_label"),
        FieldPanel("col_updated_label"),
        FieldPanel("empty_state_text"),
        FieldPanel("empty_state_link_text"),
        FieldPanel("create_heading"),
        FieldPanel("create_subtext"),
        FieldPanel("edit_heading"),
        FieldPanel("edit_subtext_prefix"),
        FieldPanel("draft_button_text"),
        FieldPanel("publish_button_text"),
        FieldPanel("update_button_text"),
        FieldPanel("back_button_text"),
        FieldPanel("field_title_label"),
        FieldPanel("field_title_placeholder"),
        FieldPanel("field_category_label"),
        FieldPanel("field_category_placeholder"),
        FieldPanel("field_featured_image_label"),
        FieldPanel("field_short_desc_label"),
        FieldPanel("field_short_desc_placeholder"),
        FieldPanel("field_body_label"),
        FieldPanel("field_body_placeholder"),
    ]

    parent_page_types = ["companies.CompanyHomePage", "wagtailcore.Page"]
    subpage_types = []
    template = "blogs/blog_posts.html"

    def serve(self, request):
        from django.shortcuts import redirect, render
        from Apps.blogs.models import BlogPage, BlogIndexPage
        from Apps.accounts.models import UserDashboardPage
        from Apps.companies.models import CompanyMembership

        if not request.user.is_authenticated:
            return redirect("/login/")

        blogs = BlogPage.objects.all().select_related('author', 'featured_image', 'category').order_by('-latest_revision_created_at')

        membership = CompanyMembership.objects.filter(user=request.user).select_related('company').first()
        blog_index_id = None
        if membership:
            blogs = blogs.filter(company=membership.company)
            home = membership.company.home_pages.first()
            if home:
                blog_index = BlogIndexPage.objects.filter(path__startswith=home.path).first()
                blog_index_id = blog_index.id if blog_index else None
        else:
            first_index = BlogIndexPage.objects.first()
            blog_index_id = first_index.id if first_index else None

        dashboard_page = UserDashboardPage.objects.live().first()
        sidebar_links = dashboard_page.sidebar_links if dashboard_page else []

        context = self.get_context(request)
        context.update({
            'page': self,
            'dashboard_page': dashboard_page,
            'sidebar_links': sidebar_links,
            'user': request.user,
            'blogs': blogs,
            'blog_index_id': blog_index_id,
            'active_tab': 'posts',
        })
        return render(request, self.template, context)

    class Meta:
        verbose_name = "Company Blog Posts Page"