from django.apps import AppConfig


class LabTestsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lab_tests'
    verbose_name = 'Лабораторные исследования'
    
    def ready(self):
        """Регистрируем сигналы при запуске приложения"""
        try:
            import lab_tests.signals
        except ImportError:
            pass