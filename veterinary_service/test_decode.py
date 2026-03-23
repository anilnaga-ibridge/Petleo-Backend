import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from django.conf import settings
print("AUTH_SERVICE_URL:", getattr(settings, 'AUTH_SERVICE_URL', None))
# Check if the veterinary service has a custom permission class handling this error
