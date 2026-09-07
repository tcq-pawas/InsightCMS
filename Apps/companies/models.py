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


# ---------------------------------------------------------------------------
# Company (original model — must stay here, admin.py imports it from here)
# ---------------------------------------------------------------------------
class Company(BaseModel):
    """Company model representing external websites (Tenants)."""

    class Status(models.TextChoices):
        ACTIVE   = 'active',   _('Active')
        INACTIVE = 'inactive', _('Inactive')

    company_name   = models.CharField(max_length=255, verbose_name=_('Company Name'))
    slug           = models.SlugField(max_length=255, unique=True, blank=True, null=True, verbose_name=_('Slug'))
    domain         = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Domain'))
    website_name   = models.CharField(max_length=255, verbose_name=_('Website Name'))
    website_url    = models.URLField(max_length=500,  verbose_name=_('Website URL'))
    logo           = models.ImageField(upload_to='company_logos/', blank=True, null=True, verbose_name=_('Logo'))
    email          = models.EmailField(verbose_name=_('Email'))
    contact_person = models.CharField(max_length=255, verbose_name=_('Contact Person'))
    status         = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name=_('Status'),
    )
    api_key = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        verbose_name=_('API Key'),
    )

    class Meta:
        verbose_name        = _('Company')
        verbose_name_plural = _('Companies')
        ordering            = ['-created_at']

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = generate_api_key()
        super().save(*args, **kwargs)

    def regenerate_api_key(self):
        """Regenerate the API key for this company."""
        self.api_key = generate_api_key()
        self.save()


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
            'sidebar_links': sidebar_links,
            'user': request.user,
            'blogs': blogs,
            'blog_index_id': blog_index_id,
            'active_tab': 'posts',
        })
        return render(request, self.template, context)

    class Meta:
        verbose_name = "Company Blog Posts Page"