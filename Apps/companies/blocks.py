"""
Apps/companies/blocks.py

StreamField block definitions for CompanyHomePage.
Lives in the `companies` app since CompanyHomePage itself belongs here
(it represents a company's public website, not a blog content type).
"""
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


# ---------------------------------------------------------------------------
# 1. Hero
# ---------------------------------------------------------------------------
class HeroFlowCardBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, max_length=50, label=_("Title"), default="Dashboard")
    subtitle = blocks.CharBlock(required=False, max_length=60, label=_("Subtitle"), default="Manage Blogs")
    icon_name = blocks.ChoiceBlock(
        choices=[
            ("bars", "Dashboard / Bars"),
            ("gear", "API / Gear"),
            ("desktop", "Website / Desktop"),
            ("users", "Visitors / Users"),
            ("bolt", "Lightning / Bolt"),
        ],
        default="bars",
        label=_("Icon"),
    )
    color_theme = blocks.ChoiceBlock(
        choices=[
            ("purple", "Purple"),
            ("orange", "Orange"),
            ("blue", "Blue"),
            ("pink", "Pink"),
        ],
        default="purple",
        label=_("Color Theme"),
    )

    class Meta:
        icon = "tag"
        label = "Flow Card"


class HeroBlock(blocks.StructBlock):
    badge_text = blocks.CharBlock(
        required=False, max_length=60, label=_("Badge text"),
        help_text=_("Small pill shown above the heading, e.g. "
                     "'The Complete Blog Management Platform'."),
    )
    heading = blocks.CharBlock(
        required=True, max_length=120, label=_("Heading")
    )
    heading_highlight = blocks.CharBlock(
        required=False, max_length=120, label=_("Heading (gradient part)"),
        help_text=_("Optional second line/phrase shown in the "
                     "purple-orange gradient, e.g. 'Power Your Website.'"),
    )
    description = blocks.TextBlock(
        required=False, label=_("Description"),
        help_text=_("Short supporting text under the heading."),
    )
    cta_text = blocks.CharBlock(
        required=False, max_length=50, label=_("Primary button text"),
        default="Get Started",
    )
    cta_link = blocks.URLBlock(
        required=False, label=_("Primary button link"),
    )
    secondary_cta_text = blocks.CharBlock(
        required=False, max_length=50, label=_("Secondary button text"),
        default="View Dashboard",
    )
    secondary_cta_link = blocks.URLBlock(
        required=False, label=_("Secondary button link"),
    )
    subtext = blocks.CharBlock(
        required=False, max_length=120, label=_("Subtext (below buttons)"),
        default="Create once. Publish everywhere.",
        help_text=_("Optional small subtext shown under CTA buttons with checkmark icon."),
    )
    image = ImageChooserBlock(required=False, label=_("Hero image"))
    flow_cards = blocks.ListBlock(HeroFlowCardBlock(), required=False, label=_("Workflow Cards (Bottom)"))

    class Meta:
        template = "companies/blocks/hero_block.html"
        icon = "image"
        label = "Hero"


# ---------------------------------------------------------------------------
# 2. About / Rich text
# ---------------------------------------------------------------------------
class AboutBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False, max_length=120, default="About Us")
    body = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic", "link", "ol", "ul", "h3", "h4"],
        label=_("Content"),
    )
    image = ImageChooserBlock(required=False, label=_("Side image"))

    class Meta:
        template = "companies/blocks/about_block.html"
        icon = "doc-full"
        label = "About / Rich Text"


# ---------------------------------------------------------------------------
# 3. Services / feature cards
# ---------------------------------------------------------------------------
class ServiceCardBlock(blocks.StructBlock):
    icon = ImageChooserBlock(required=False, label=_("Icon"))
    title = blocks.CharBlock(required=True, max_length=80)
    description = blocks.TextBlock(required=False)

    class Meta:
        icon = "cog"
        label = "Service Card"


class ServicesBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False, max_length=120, default="Our Services")
    subheading = blocks.CharBlock(required=False, max_length=200)
    cards = blocks.ListBlock(ServiceCardBlock())

    class Meta:
        template = "companies/blocks/services_block.html"
        icon = "list-ul"
        label = "Services / Feature Cards"


# ---------------------------------------------------------------------------
# 4. Testimonials
# ---------------------------------------------------------------------------
class TestimonialCardBlock(blocks.StructBlock):
    quote = blocks.TextBlock(required=True)
    author_name = blocks.CharBlock(required=True, max_length=80)
    author_role = blocks.CharBlock(required=False, max_length=100)
    author_image = ImageChooserBlock(required=False)

    class Meta:
        icon = "openquote"
        label = "Testimonial"


class TestimonialsBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False, max_length=120, default="What our clients say")
    testimonials = blocks.ListBlock(TestimonialCardBlock())

    class Meta:
        template = "companies/blocks/testimonials_block.html"
        icon = "openquote"
        label = "Testimonials"


# ---------------------------------------------------------------------------
# 5. Blog preview (data-driven, scoped to the current company)
# ---------------------------------------------------------------------------
class BlogPreviewBlock(blocks.StructBlock):
    heading = blocks.CharBlock(
        required=False, max_length=120, default="Latest from our Blog"
    )
    subheading = blocks.CharBlock(required=False, max_length=200)
    number_of_posts = blocks.IntegerBlock(
        default=3, min_value=1, max_value=12,
        label=_("Number of posts to show"),
    )
    read_more_text = blocks.CharBlock(
        required=False, max_length=40, default="Read More",
        label=_("Button / Link Text"),
    )
    empty_message = blocks.CharBlock(
        required=False, max_length=150, default="No blog posts published yet.",
        label=_("Empty State Message"),
    )

    def get_context(self, value, parent_context=None):
        """
        Pull the latest LIVE, PUBLIC blog posts that belong to the current
        company only.

        Two-layer scoping (both required):
          1. Subtree  - post must live under this company's own site/page
             tree (via its BlogIndexPage), so cross-company leakage can't
             happen even if a page was filed in the wrong place.
          2. Company FK - the post's `company` field must equal
             `page.company`, as a second, independent check.

        NOTE: BlogPage lives in the `blogs` app, imported lazily here to
        avoid a circular import between `companies` and `blogs`.
        """
        context = super().get_context(value, parent_context=parent_context)
        page = context.get("page")
        posts = []

        if page is not None and getattr(page, "company_id", None):
            from Apps.blogs.models import BlogPage

            site = page.get_site()
            site_root = site.root_page if site else page.get_root()

            posts_qs = (
                BlogPage.objects.live()
                .public()
                .descendant_of(site_root)
                .filter(company_id=page.company_id)
                .order_by("-first_published_at")
            )
            posts = list(posts_qs[: value["number_of_posts"]])

        context["posts"] = posts
        return context

    class Meta:
        template = "companies/blocks/blog_preview_block.html"
        icon = "doc-full-inverse"
        label = "Blog Preview"


# ---------------------------------------------------------------------------
# 6. Contact / CTA
# ---------------------------------------------------------------------------
class ContactCTABlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False, max_length=120, default="Let's talk")
    description = blocks.TextBlock(required=False)
    button_text = blocks.CharBlock(required=False, max_length=50, default="Contact Us")
    button_link = blocks.URLBlock(required=False)
    phone = blocks.CharBlock(required=False, max_length=30)
    email = blocks.EmailBlock(required=False)

    class Meta:
        template = "companies/blocks/contact_cta_block.html"
        icon = "mail"
        label = "Contact / CTA"


# ---------------------------------------------------------------------------
# 7. Footer
# ---------------------------------------------------------------------------
class SocialLinkBlock(blocks.StructBlock):
    platform = blocks.ChoiceBlock(
        choices=[
            ("facebook", "Facebook"),
            ("twitter", "Twitter / X"),
            ("linkedin", "LinkedIn"),
            ("instagram", "Instagram"),
            ("youtube", "YouTube"),
            ("other", "Other"),
        ],
        default="facebook",
    )
    url = blocks.URLBlock(required=True)

    class Meta:
        icon = "link"
        label = "Social Link"


class FooterLinkBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True, max_length=80, label=_("Link Text"))
    url   = blocks.URLBlock(required=True, label=_("URL"))

    class Meta:
        icon  = "link"
        label = "Link"


class FooterColumnBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=True, max_length=60, label=_("Column Heading"))
    links   = blocks.ListBlock(FooterLinkBlock(), label=_("Links"))

    class Meta:
        icon  = "list-ul"
        label = "Footer Column"


class FooterBlock(blocks.StructBlock):
    brand_name          = blocks.CharBlock(required=False, max_length=60, default="InsightCMS", label=_("Brand Name"))
    company_description = blocks.TextBlock(required=False, label=_("Company Description"))
    address             = blocks.CharBlock(required=False, max_length=255, label=_("Address"))
    phone               = blocks.CharBlock(required=False, max_length=30, label=_("Phone"))
    email               = blocks.EmailBlock(required=False, label=_("Email"))
    social_links        = blocks.ListBlock(SocialLinkBlock(), label=_("Social Links"))
    link_columns        = blocks.ListBlock(FooterColumnBlock(), required=False, label=_("Link Columns (e.g. Product, Company)"))
    copyright_text      = blocks.CharBlock(required=False, max_length=200, label=_("Copyright Text"))

    class Meta:
        template = "companies/blocks/footer_block.html"
        icon     = "site"
        label    = "Footer"


# ---------------------------------------------------------------------------
# Top-level StreamField block choices for CompanyHomePage.body
# ---------------------------------------------------------------------------
COMPANY_HOME_PAGE_BLOCKS = [
    ("hero", HeroBlock()),
    ("about", AboutBlock()),
    ("services", ServicesBlock()),
    ("testimonials", TestimonialsBlock()),
    ("blog_preview", BlogPreviewBlock()),
    ("contact_cta", ContactCTABlock()),
    ("footer", FooterBlock()),
]