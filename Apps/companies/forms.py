"""
Apps/companies/forms.py

Restricts the "Company" field dropdown on page-edit forms so a
non-superuser only ever sees companies they're a member of. This is
the 4th sub-requirement of Section 4:
    "restrict the Company field in Wagtail page forms."

Usage: attach this as `base_form_class` on any Page model that has a
`company` ForeignKey field — e.g. CompanyHomePage. Wagtail automatically
passes the logged-in user into the form as `for_user` when building the
edit view, so we override __init__ to narrow the queryset there.
"""
from wagtail.admin.forms import WagtailAdminPageForm


class CompanyScopedPageForm(WagtailAdminPageForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        user = getattr(self, "for_user", None)
        if user is None or "company" not in self.fields:
            return

        if user.is_superuser:
            return  # sees every company, unrestricted

        from Apps.companies.models import CompanyMembership
        from Apps.companies.models import Company

        company_ids = CompanyMembership.objects.filter(user=user).values_list(
            "company_id", flat=True
        )
        self.fields["company"].queryset = Company.objects.filter(id__in=company_ids)