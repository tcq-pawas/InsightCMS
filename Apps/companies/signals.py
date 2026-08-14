"""
Apps/companies/signals.py

Implements Section 2 of the workflow doc:
"Create one Wagtail Site and one page subtree per company. Each
company's Wagtail Site points at its own CompanyHomePage."

Whenever a CompanyHomePage is saved, we automatically create (or update)
a matching wagtailcore.Site record:
    hostname   = derived from company.website_url
    root_page  = this CompanyHomePage
    is_default_site = False   (unless it's the very first site ever)

This means a developer/admin never has to manually visit
Settings > Sites in the Wagtail admin — the Site is kept in sync with
the page automatically.

Uses the EXISTING `website_url` field on Company (no new migration
needed) — e.g. "https://abc.com" -> hostname "abc.com".
"""
from urllib.parse import urlparse

from django.db.models.signals import post_save
from django.dispatch import receiver

from wagtail.models import Site


def hostname_from_website_url(website_url):
    """
    Turn "https://abc.com/" or "http://abc.com" into "abc.com".
    Returns None if website_url is empty or unparseable.
    """
    if not website_url:
        return None
    parsed = urlparse(website_url)
    return parsed.netloc or parsed.path or None


def sync_site_for_home_page(home_page):
    """
    Create or update the Wagtail Site that should point at this
    CompanyHomePage, based on the linked Company's website_url.
    """
    company = home_page.company
    hostname = hostname_from_website_url(getattr(company, "website_url", None))

    if not hostname:
        # No usable URL yet — nothing to sync. The page still works
        # fine in the admin; it just isn't wired to a public hostname
        # until the company has a website_url set.
        return

    # There should be at most one Site per company. Look it up by the
    # page's own id first (in case the URL changed), falling back to
    # hostname lookup.
    site = Site.objects.filter(root_page=home_page).first()
    if site is None:
        site = Site.objects.filter(hostname=hostname).first()

    is_first_site_ever = not Site.objects.exists()

    if site is None:
        Site.objects.create(
            hostname=hostname,
            port=80,
            root_page=home_page,
            site_name=getattr(company, "company_name", hostname),
            is_default_site=is_first_site_ever,
        )
    else:
        site.hostname = hostname
        site.root_page = home_page
        site.site_name = getattr(company, "company_name", hostname)
        site.save()


@receiver(post_save, sender="companies.CompanyHomePage")
def on_company_home_page_saved(sender, instance, **kwargs):
    """
    Keep the Wagtail Site in sync every time a CompanyHomePage is saved
    (including when it's published from a draft revision).
    """
    sync_site_for_home_page(instance)