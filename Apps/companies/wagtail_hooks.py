"""
Apps/companies/wagtail_hooks.py

Implements the remaining part of Section 4:
  - only show the user's own company pages in the page explorer/search
  - block direct URL access to another company's page
  - restrict the "Company" field so an editor can't select another
    company on CompanyHomePage

Platform administrators (Django superusers) are exempt from all of
these restrictions and continue to see everything.
"""
from wagtail import hooks


def _user_company_ids(user):
    """Company ids this user has ANY membership in (manager or editor)."""
    if user.is_superuser:
        return None  # sentinel meaning "no restriction"
    from Apps.companies.models import CompanyMembership

    return list(
        CompanyMembership.objects.filter(user=user).values_list(
            "company_id", flat=True
        )
    )


@hooks.register("construct_explorer_page_queryset")
def filter_explorer_by_company(parent_page, pages, request):
    """
    Restricts the Wagtail page explorer tree so a user only sees pages
    under CompanyHomePages they belong to, or the specific home pages themselves.
    Superusers see everything.
    """
    company_ids = _user_company_ids(request.user)
    if company_ids is None:
        return pages  # superuser — unrestricted

    from Apps.companies.models import CompanyHomePage

    allowed_home_pages = CompanyHomePage.objects.filter(company_id__in=company_ids)
    allowed_paths = [hp.path for hp in allowed_home_pages]

    if not allowed_paths:
        return pages.none()

    from django.db.models import Q

    query = Q()
    for path in allowed_paths:
        query |= Q(path__startswith=path)
        ancestors_paths = [path[:i] for i in range(4, len(path) + 1, 4) if path[:i]]
        for ap in ancestors_paths:
            query |= Q(path=ap)

    filtered_pages = pages.filter(query)

    all_other_home_pages = CompanyHomePage.objects.exclude(company_id__in=company_ids)
    other_home_page_ids = [hp.id for hp in all_other_home_pages]
    if other_home_page_ids:
        filtered_pages = filtered_pages.exclude(id__in=other_home_page_ids)

    return filtered_pages


@hooks.register("construct_page_listing_buttons")
def hide_buttons_for_other_companies(buttons, page, *args, **kwargs):
    context = kwargs.get("context")
    if not context and len(args) > 1 and isinstance(args[-1], dict):
        context = args[-1]

    request = context.get("request") if context else None
    if request is None or request.user.is_superuser:
        return buttons

    company_ids = _user_company_ids(request.user)
    if company_ids is None:
        return buttons

    from Apps.companies.models import CompanyHomePage

    allowed_home_pages = CompanyHomePage.objects.filter(company_id__in=company_ids)
    allowed_paths = [hp.path for hp in allowed_home_pages]

    if not any(page.path.startswith(p) for p in allowed_paths):
        return []
    return buttons


@hooks.register("before_edit_page")
def block_cross_company_edit(request, page):
    if request.user.is_superuser:
        return None

    company_ids = _user_company_ids(request.user)
    if company_ids is None:
        return None

    from Apps.companies.models import CompanyHomePage
    from django.core.exceptions import PermissionDenied

    allowed_home_pages = CompanyHomePage.objects.filter(company_id__in=company_ids)
    allowed_paths = [hp.path for hp in allowed_home_pages]

    if not any(page.path.startswith(p) for p in allowed_paths):
        raise PermissionDenied(
            "You do not have permission to edit this page — it belongs "
            "to a different company."
        )
    return None


@hooks.register("before_delete_page")
def block_cross_company_delete(request, page):
    return block_cross_company_edit(request, page)


def _company_ids_of_page(page):
    from Apps.companies.models import CompanyHomePage

    ancestor_home = (
        page.get_ancestors(inclusive=True)
        .type(CompanyHomePage)
        .first()
    )
    if ancestor_home is None:
        return None
    home = ancestor_home.specific
    return getattr(home, "company_id", None)


@hooks.register("before_move_page")
def block_cross_company_move(request, page, destination):
    if request.user.is_superuser:
        return None

    from django.core.exceptions import PermissionDenied

    source_company_id = _company_ids_of_page(page)
    dest_company_id = _company_ids_of_page(destination)

    if source_company_id != dest_company_id:
        raise PermissionDenied(
            "Pages cannot be moved between different companies."
        )
    return None


@hooks.register("before_copy_page")
def block_cross_company_copy(request, page):
    return None


@hooks.register("construct_page_chooser_queryset")
def restrict_page_chooser_by_company(pages, request):
    company_ids = _user_company_ids(request.user)
    if company_ids is None:
        return pages

    from Apps.companies.models import CompanyHomePage
    from django.db.models import Q

    allowed_home_pages = CompanyHomePage.objects.filter(company_id__in=company_ids)
    allowed_paths = [hp.path for hp in allowed_home_pages]

    if not allowed_paths:
        return pages.none()

    query = Q()
    for path in allowed_paths:
        query |= Q(path__startswith=path)
    return pages.filter(query)


@hooks.register("construct_homepage_panels")
def add_company_workspace_panel(request, panels):
    from Apps.companies.dashboard import CompanyWorkspacePanel

    panels.append(CompanyWorkspacePanel())
    return panels


# ---------------------------------------------------------------------------
# Company Snippet — Settings menu, profile view, approval status
# ---------------------------------------------------------------------------
from django.urls import reverse
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, InspectView, IndexView
from wagtail.admin.panels import FieldPanel
from Apps.companies.models import Company, CompanyMembership


class CompanyInspectView(InspectView):
    """
    Read-only profile card. This is Wagtail's built-in 'Inspect' view —
    perfect for showing details without allowing edits directly.
    """
    template_name = "companies/company_profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["company"] = self.object
        context["edit_url"] = reverse(
            self.edit_url_name, args=[self.object.pk]
        )
        return context


class CompanyIndexView(IndexView):
    """
    Makes clicking a row in the Companies list open the Inspect
    (profile) view instead of the default Edit form.
    """
    def get_edit_url(self, instance):
        return reverse(
            self.inspect_url_name, args=[instance.pk]
        )
        

class CompanyViewSet(SnippetViewSet):
    model = Company
    icon = "site"
    menu_label = "Companies"
    menu_name = "companies"
    menu_order = 100
    add_to_settings_menu = True
    list_display = ["company_name", "website_name", "status", "approval_status", "created_at"]
    search_fields = ["company_name", "email", "website_name"]
    inspect_view_enabled = True
    inspect_view_class = CompanyInspectView
    index_view_class = CompanyIndexView
    list_export = []

    panels = [
        FieldPanel("company_name"),
        FieldPanel("website_name"),
        FieldPanel("website_url"),
        FieldPanel("logo"),
        FieldPanel("email"),
        FieldPanel("contact_person"),
        FieldPanel("status"),
        FieldPanel("approval_status"),
        FieldPanel("domain"),
        FieldPanel("slug"),
        FieldPanel("api_key", read_only=True),
    ]

    def get_queryset(self, request):
        """
        Superadmin sees ALL companies.
        Non-superusers only see companies they belong to.
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        company_ids = CompanyMembership.objects.filter(
            user=request.user
        ).values_list("company_id", flat=True)
        return qs.filter(id__in=company_ids)


register_snippet(CompanyViewSet)

from django.views.generic import ListView
from wagtail.admin.menu import MenuItem
from wagtail.admin.ui.tables import Table, Column
from django.urls import path
from django.http import HttpResponseRedirect
from django.urls import reverse



class PendingCompaniesView(ListView):
    """
    Lists only companies whose approval_status is 'pending'.
    """
    model = Company
    template_name = "companies/pending_companies.html"
    context_object_name = "companies"

    def get_queryset(self):
        return Company.objects.filter(approval_status="pending").order_by("-created_at")

    def post(self, request, *args, **kwargs):
        company_id = request.POST.get("company_id")
        action = request.POST.get("action")

        company = Company.objects.get(pk=company_id)
        if action == "approve":
            company.approval_status = "approved"
            company.save()
            
            # Also approve the users linked to this company
            from Apps.companies.models import CompanyMembership
            member_user_ids = CompanyMembership.objects.filter(
                company=company
            ).values_list("user_id", flat=True)

            from django.contrib.auth import get_user_model
            User = get_user_model()
            User.objects.filter(id__in=member_user_ids).update(is_approved=True)
            
        elif action == "reject":
            company.approval_status = "rejected"
            company.save()
            
            # Also reject (keep unapproved) the users linked to this company
            from Apps.companies.models import CompanyMembership
            member_user_ids = CompanyMembership.objects.filter(
                company=company
            ).values_list("user_id", flat=True)

            from django.contrib.auth import get_user_model
            User = get_user_model()
            User.objects.filter(id__in=member_user_ids).update(is_approved=False)

        return HttpResponseRedirect(reverse("pending_companies"))

@hooks.register("register_admin_urls")
def register_pending_companies_url():
    return [
        path(
            "companies/pending/",
            PendingCompaniesView.as_view(),
            name="pending_companies",
        ),
    ]


@hooks.register("register_admin_menu_item")
def register_pending_companies_menu_item():
    return MenuItem(
        "Pending Verification",
        reverse("pending_companies"),
        icon_name="warning",
        order=200,
    )