from django.apps import AppConfig


class DocumentSignaturesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'document_signatures'
    
    def ready(self):
        """
        Импортируем сигналы при запуске приложения
        """
        import document_signatures.signals
