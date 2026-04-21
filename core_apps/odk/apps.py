from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OdkConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core_apps.odk"
    verbose_name = _("Open Data kit")

    def ready(self):
        # try:
        #     import core_apps.odk.signals  # noqa
        # except ImportError:
        pass
