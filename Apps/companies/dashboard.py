"""
Apps/companies/dashboard.py

Implements Section 5 of the workflow doc: Wagtail dashboard experience.

Adds a custom panel to the EXISTING Wagtail dashboard (/cms/) — not a
separate admin application. Each company the logged-in user is
assigned to gets its own card showing:

  - company name and logo
  - number of published posts and drafts
  - most recently changed posts
  - "Open workspace" action -> that company's BlogIndexPage
  - "New blog post" action
  - a read-only API endpoint / integration reminder

A user assigned to one company sees only that one card. A platform
administrator (superuser) sees a card for every company. The page
explorer itself is STILL the real security boundary (see
wagtail_hooks.py) — this panel is a UI convenience only.
"""
from django.template.loader import render_to_string
from django.urls import reverse

from wagtail.admin.ui.components import Component


def _companies_for_user(user):
    """
    Returns the list of Company objects this user should see a
    dashboard card for. Superusers see every company; everyone else
    sees only the companies they have a CompanyMembership in.
    """
    from Apps.companies.models import Company, CompanyMembership

    if user.is_superuser:
        return list(Company.objects.all().order_by("company_name"))

    company_ids = CompanyMembership.objects.filter(user=user).values_list(
        "company_id", flat=True
    )
    return list(Company.objects.filter(id__in=company_ids).order_by("company_name"))


def _card_data_for_company(company, request):
    """
    Builds the context dict for a single company's dashboard card:
    counts, recent posts, and the links the card needs.
    """
    from Apps.companies.models import CompanyHomePage
    from Apps.blogs.models import BlogIndexPage, BlogPage

    home_page = CompanyHomePage.objects.filter(company=company).first()
    blog_index = None
    if home_page is not None:
        blog_index = BlogIndexPage.objects.child_of(home_page).first()

    if blog_index is not None:
        company_posts = BlogPage.objects.descendant_of(blog_index)
    else:
        # Fall back to a direct company filter if the page tree isn't
        # fully set up yet, so the card still shows sane counts.
        company_posts = BlogPage.objects.filter(company=company)

    published_count = company_posts.live().count()
    draft_count = company_posts.filter(has_unpublished_changes=True).count()
    # Pages that only ever exist as a draft (never published at all).
    never_published_count = company_posts.filter(live=False).exclude(
        has_unpublished_changes=False
    ).count()

    recent_posts = company_posts.order_by("-latest_revision_created_at")[:5]

    open_workspace_url = None
    new_post_url = None
    if blog_index is not None:
        open_workspace_url = reverse(
            "wagtailadmin_explore", args=[blog_index.id]
        )
        new_post_url = reverse(
            "wagtailadmin_pages:add",
            args=["blogs", "blogpage", blog_index.id],
        )

    return {
        "company": company,
        "published_count": published_count,
        "draft_count": draft_count + never_published_count,
        "recent_posts": recent_posts,
        "open_workspace_url": open_workspace_url,
        "new_post_url": new_post_url,
        "blog_index_missing": blog_index is None,
    }


class CompanyWorkspacePanel(Component):
    """
    Wagtail dashboard "summary item" style panel. Registered via the
    construct_homepage_panels hook (see wagtail_hooks.py). Renders one
    card per company the current user can see.
    """

    order = 50  # sits below Wagtail's built-in panels

    def render_html(self, parent_context):
        request = parent_context["request"]
        companies = _companies_for_user(request.user)

        cards = [_card_data_for_company(company, request) for company in companies]

        return render_to_string(
            "companies/dashboard_panel.html",
            {"cards": cards, "is_superuser": request.user.is_superuser},
            request=request,
        )