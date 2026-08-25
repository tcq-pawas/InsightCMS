"""
Apps/companies/permissions.py

Implements Section 4 of the workflow doc: Tenant isolation & permissions.

NOTE: CompanyMembership is already defined in Apps/companies/models.py
(you added it there) — this file does NOT redefine it, it only imports
and uses it.

Covers:
  1. Auto-creating 2 Wagtail/Django groups per company when it's created:
       "Company <name> Managers"  -> can add/edit/publish in that subtree
       "Company <name> Editors"   -> can add/edit only, cannot publish
  2. Auto-adding/removing the user's Django group membership whenever
     their CompanyMembership is saved/deleted.
  3. Applying GroupPagePermission on the company's page subtree (root =
     that company's CompanyHomePage) so permissions inherit down to the
     BlogIndexPage and every BlogPage below it.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from django.contrib.auth.models import Group as WagtailGroup
from wagtail.models import GroupPagePermission

# ---------------------------------------------------------------------------
# 1. Group provisioning per company
# ---------------------------------------------------------------------------
def group_names_for_company(company):
    return (
        f"Company {company.company_name} Managers",
        f"Company {company.company_name} Editors",
    )


def _page_permission_object(codename):
    """
    Newer Wagtail versions store page permissions as a real Django
    `Permission` FK (via `GroupPagePermission.permission`) instead of
    the old `permission_type` string field. This resolves the correct
    Permission row for a given short codename ("add", "edit",
    "publish") against the wagtailcore.Page content type.
    """
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    from wagtail.models import Page as WagtailPage

    codename_map = {
        "add": "add_page",
        "edit": "change_page",
        "publish": "publish_page",
    }
    page_content_type = ContentType.objects.get_for_model(WagtailPage)
    return Permission.objects.get(
        codename=codename_map[codename], content_type=page_content_type
    )


def ensure_company_groups(company):
    """
    Create (if missing) the Manager/Editor Django groups for a company,
    and wire GroupPagePermission entries onto that company's page
    subtree root (its CompanyHomePage), so permissions inherit to the
    blog index and every post below it.

    Safe to call repeatedly — it's idempotent.
    """
    manager_name, editor_name = group_names_for_company(company)
    manager_group, _created = WagtailGroup.objects.get_or_create(name=manager_name)
    editor_group, _created = WagtailGroup.objects.get_or_create(name=editor_name)

    # Find this company's page-tree root. If the CompanyHomePage hasn't
    # been created yet, there's nothing to attach permissions to yet —
    # the groups still get created so memberships can be assigned, and
    # permissions get attached the next time this function runs (e.g.
    # after CompanyHomePage is saved).
    from Apps.companies.models import CompanyHomePage

    home_page = CompanyHomePage.objects.filter(company=company).first()
    if home_page is None:
        return manager_group, editor_group

    # Wagtail's built-in permission types we assign at the subtree root
    permission_types = ["add", "edit", "publish"]

    # Managers: add + edit + publish page permissions
    for perm_type in permission_types:
        GroupPagePermission.objects.get_or_create(
            group=manager_group,
            page=home_page,
            permission=_page_permission_object(perm_type),
        )

    # Editors: add + edit page permissions only, never publish
    for perm_type in ["add", "edit"]:
        GroupPagePermission.objects.get_or_create(
            group=editor_group,
            page=home_page,
            permission=_page_permission_object(perm_type),
        )
    # Make sure editors do NOT retain a stray publish permission from an
    # earlier run/config change.
    GroupPagePermission.objects.filter(
        group=editor_group,
        page=home_page,
        permission=_page_permission_object("publish"),
    ).delete()

    # Assign Wagtail Image and Document management permissions to both groups
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    try:
        from wagtail.images.models import Image
        from wagtail.documents.models import Document
        
        image_ct = ContentType.objects.get_for_model(Image)
        doc_ct = ContentType.objects.get_for_model(Document)
        
        # Grant Wagtail Admin Access, Images and Documents permissions
        admin_access_perm = Permission.objects.filter(codename="access_admin").first()
        image_perms = Permission.objects.filter(content_type=image_ct, codename__in=["add_image", "change_image", "choose_image"])
        doc_perms = Permission.objects.filter(content_type=doc_ct, codename__in=["add_document", "change_document", "choose_document"])
        
        for group in [manager_group, editor_group]:
            if admin_access_perm:
                group.permissions.add(admin_access_perm)
            group.permissions.add(*image_perms)
            group.permissions.add(*doc_perms)
    except Exception:
        pass

    return manager_group, editor_group


# ---------------------------------------------------------------------------
# 4. Editorial approval workflow per company (Section 7)
#
# "If formal approvals are required, configure a Wagtail workflow on
#  each company blog index. Editors submit; managers approve/publish."
# ---------------------------------------------------------------------------
def ensure_company_workflow(company):
    """
    Creates (if missing) a Wagtail Workflow for this company with a
    single GroupApprovalTask assigned to the company's Managers group,
    then assigns that workflow to the company's BlogIndexPage so it
    automatically covers every blog post beneath it.

    Safe to call repeatedly — it's idempotent. If the company doesn't
    have a BlogIndexPage yet, the Workflow/Task are still created so
    they exist, and the page assignment happens next time this runs
    (e.g. after the BlogIndexPage is created).
    """
    from wagtail.models import Workflow, WorkflowTask, WorkflowPage, GroupApprovalTask

    manager_group, _editor_group = ensure_company_groups(company)

    task_name = f"Company {company.company_name} Manager Approval"
    approval_task, _created = GroupApprovalTask.objects.get_or_create(
        name=task_name
    )
    approval_task.groups.add(manager_group)

    workflow_name = f"Company {company.company_name} Blog Approval"
    workflow, _created = Workflow.objects.get_or_create(name=workflow_name)

    WorkflowTask.objects.get_or_create(
        workflow=workflow, task=approval_task, sort_order=0
    )

    from Apps.companies.models import CompanyHomePage
    from Apps.blogs.models import BlogIndexPage

    home_page = CompanyHomePage.objects.filter(company=company).first()
    blog_index = None
    if home_page is not None:
        blog_index = BlogIndexPage.objects.child_of(home_page).first()

    if blog_index is not None:
        WorkflowPage.objects.get_or_create(workflow=workflow, page=blog_index)

    return workflow


@receiver(post_save, sender="companies.Company")
def on_company_saved(sender, instance, created, **kwargs):
    """
    Every time a Company is created/updated, make sure its two groups
    (and page permissions, once the home page exists) are in sync, and
    make sure its approval workflow exists (and is attached to its
    BlogIndexPage, once that page exists).
    """
    ensure_company_groups(instance)
    ensure_company_workflow(instance)


# ---------------------------------------------------------------------------
# 3. Keep user <-> Django group membership in sync with CompanyMembership
# ---------------------------------------------------------------------------
@receiver(post_save, sender="companies.CompanyMembership")
def on_membership_saved(sender, instance, **kwargs):
    manager_group, editor_group = ensure_company_groups(instance.company)

    # Remove from both first (covers role changes: editor -> manager etc.)
    instance.user.groups.remove(manager_group, editor_group)

    from Apps.companies.models import CompanyMembership

    target_group = (
        manager_group if instance.role == CompanyMembership.Role.MANAGER
        else editor_group
    )
    instance.user.groups.add(target_group)
    if not instance.user.is_staff:
        instance.user.is_staff = True
        instance.user.save(update_fields=["is_staff"])


@receiver(post_delete, sender="companies.CompanyMembership")
def on_membership_deleted(sender, instance, **kwargs):
    manager_group, editor_group = ensure_company_groups(instance.company)
    instance.user.groups.remove(manager_group, editor_group)


# ---------------------------------------------------------------------------
# Re-sync the workflow when a BlogIndexPage is saved, since it usually
# doesn't exist yet at the moment the Company itself is first created.
# ---------------------------------------------------------------------------
@receiver(post_save, sender="blogs.BlogIndexPage")
def on_blog_index_page_saved(sender, instance, **kwargs):
    company = getattr(instance, "company", None)
    if company is not None:
        ensure_company_workflow(company)