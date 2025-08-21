from django.apps import AppConfig


class InstrumentalProceduresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'instrumental_procedures'
    verbose_name = 'Инструментальные исследования'
    
    def ready(self):
        """Регистрируем сигналы при запуске приложения"""
        try:
            import instrumental_procedures.signals
        except ImportError:
            pass