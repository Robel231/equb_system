from django.apps import AppConfig

class EqubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'equb'

    def ready(self):
        import equb.signals  # Import signals to connect them