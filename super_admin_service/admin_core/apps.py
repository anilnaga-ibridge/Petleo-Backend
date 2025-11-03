from django.apps import AppConfig


class AdminCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_core'

    def ready(self):
        import admin_core.signals