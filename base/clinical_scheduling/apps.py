from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ClinicalSchedulingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clinical_scheduling'
    verbose_name = _('Клиническое расписание')
