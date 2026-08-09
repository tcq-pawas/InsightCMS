from django.db import models
from django.utils.translation import gettext_lazy as _
from Apps.common.models import BaseModel
from Apps.common.helpers import generate_api_key


class Company(BaseModel):
    """Company model representing external websites."""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')

    company_name = models.CharField(max_length=255, verbose_name=_('Company Name'))
    website_name = models.CharField(max_length=255, verbose_name=_('Website Name'))
    website_url = models.URLField(max_length=500, verbose_name=_('Website URL'))
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True, verbose_name=_('Logo'))
    email = models.EmailField(verbose_name=_('Email'))
    contact_person = models.CharField(max_length=255, verbose_name=_('Contact Person'))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name=_('Status')
    )
    api_key = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        verbose_name=_('API Key')
    )

    class Meta:
        verbose_name = _('Company')
        verbose_name_plural = _('Companies')
        ordering = ['-created_at']

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
