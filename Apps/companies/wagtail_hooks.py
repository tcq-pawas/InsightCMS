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
    under CompanyHomePages they belong to. Superusers see everything.
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
    return pages.filter(query)


@hooks.register("construct_page_listing_buttons")
def hide_buttons_for_other_companies(buttons, page, page_perms, context=None, **kwargs):
    """
    Defence-in-depth for the listing UI: if for any reason a page from
    another company briefly appears (e.g. via search), don't offer
    action buttons for it unless the user is actually permitted.
    """
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
        return []  # no action buttons at all for out-of-scope pages
    return buttons


@hooks.register("before_edit_page")
def block_cross_company_edit(request, page):
    """
    Server-side guard: even if someone edits the URL directly to try to
    open another company's page for editing, deny it outright rather
    than silently rendering it.

    Returning an HttpResponse from this hook short-circuits the normal
    edit view.
    """
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


# ---------------------------------------------------------------------------
# NOTE on restricting the "Company" field dropdown:
#
# Wagtail hooks don't give clean access to the in-progress edit form, so
# the Company field restriction is implemented as a custom form class
# (CompanyScopedPageForm) attached directly to CompanyHomePage /
# BlogPage via `base_form_class`. See Apps/companies/forms.py.
# ---------------------------------------------------------------------------


def _company_ids_of_page(page):
    """
    Walk up from any page to find which company(ies) it belongs to,
    by locating the nearest CompanyHomePage ancestor.
    """
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
    """
    Prevents moving a page (e.g. a BlogPage or BlogIndexPage) out of its
    own company's subtree into another company's subtree — even for
    users who otherwise have edit rights on both ends individually.
    """
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
    """
    The Move/Copy destination picker uses Wagtail's page chooser, which
    is restricted separately below (restrict_page_chooser_by_company).
    Restricting the chooser itself is the primary defence — a user
    simply never sees another company's pages as valid destinations.
    """
    return None


@hooks.register("construct_page_chooser_queryset")
def restrict_page_chooser_by_company(pages, request):
    """
    Restricts the page chooser used by Move / Copy / "choose a parent
    page" dialogs so a non-superuser only ever sees pages within their
    own company's subtree(s) as valid destinations. This is what
    actually prevents moving or copying a post into another company —
    the other company's pages are simply never offered as a choice.
    """
    company_ids = _user_company_ids(request.user)
    if company_ids is None:
        return pages  # superuser — unrestricted

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