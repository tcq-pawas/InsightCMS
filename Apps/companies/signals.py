"""
Apps/companies/signals.py

Implements Section 2 of the workflow doc:
"Create one Wagtail Site and one page subtree per company. Each
company's Wagtail Site points at its own CompanyHomePage."

Whenever a CompanyHomePage is saved, this automatically creates (or
updates) a matching wagtailcore.Site record:
    hostname         = company.domain
    root_page        = this CompanyHomePage
    is_default_site  = True only if this is the very first Site ever
                        created in the project; False otherwise

This means a developer/admin never has to manually visit
Settings > Sites in the Wagtail admin — the Site stays in sync with
the page automatically.

Uses the `domain` field on Company (e.g. "abc.com" or
"abc.platform.com").
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from wagtail.models import Site


def sync_site_for_home_page(home_page):
    """
    Create or update the Wagtail Site that should point at this
    CompanyHomePage, based on the linked Company's domain field.
    """
    company = home_page.company
    if company is None:
        # company is optional on CompanyHomePage — nothing to sync yet.
        return

    domain = getattr(company, "domain", None)
    if not domain:
        # No domain set on the company yet — nothing to sync. The page
        # still works fine in the admin; it just isn't wired to a
        # public hostname until a domain is added.
        return

    # There should be at most one Site per company. Look it up by the
    # page's own id first (covers the case where the domain changed),
    # falling back to a hostname lookup.
    site = Site.objects.filter(root_page=home_page).first()
    if site is None:
        site = Site.objects.filter(hostname=domain).first()

    is_first_site_ever = not Site.objects.exists()

    if site is None:
        Site.objects.create(
            hostname=domain,
            port=80,
            root_page=home_page,
            site_name=getattr(company, "company_name", domain),
            is_default_site=is_first_site_ever,
        )
    else:
        site.hostname = domain
        site.root_page = home_page
        site.site_name = getattr(company, "company_name", domain)
        site.save()


@receiver(post_save, sender="companies.CompanyHomePage")
def on_company_home_page_saved(sender, instance, **kwargs):
    """
    Keep the Wagtail Site in sync every time a CompanyHomePage is saved
    (including when it's published from a draft revision).
    """
    sync_site_for_home_page(instance)