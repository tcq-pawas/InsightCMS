from django.apps import AppConfig


class CompaniesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Apps.companies'
    verbose_name = 'Companies'

    def ready(self):                               
        import Apps.companies.signals
        import Apps.companies.permissions