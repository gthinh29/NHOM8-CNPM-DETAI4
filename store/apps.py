from django.apps import AppConfig


class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'
    
from django.apps import AppConfig

class StoreConfig(AppConfig):
    name = 'store'

    def ready(self):
        import store.signals  # Import các signal
