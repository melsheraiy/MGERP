# cashflow/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class CashflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cashflow'
    verbose_name = _('Cash Flow Management') # Verbose name in Arabic

    def ready(self):
        # Import signals here if you have any
        # For example: from . import signals
        pass

