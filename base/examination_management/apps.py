from django.apps import AppConfig


class ExaminationManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'examination_management'
    verbose_name = 'Управление обследованиями'
    
    def ready(self):
        """Регистрируем сигналы при запуске приложения"""
        try:
            import examination_management.signals
        except ImportError:
            pass
