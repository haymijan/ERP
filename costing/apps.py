# costing/apps.py

from django.apps import AppConfig

class CostingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'costing'

    # --- নতুন এই অংশটুকু যোগ করুন ---
    def ready(self):
        import costing.signals