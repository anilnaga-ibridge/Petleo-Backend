
from django.apps import AppConfig

class VeterinaryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'veterinary'

    def ready(self):
        import veterinary.billing
        import veterinary.audit
