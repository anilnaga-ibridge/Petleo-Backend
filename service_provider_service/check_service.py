import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import Service

def check_service():
    sid = '8da6c82b-2136-4a14-9670-2973682107a6'
    print(f"--- Checking Service {sid} ---")
    try:
        s = Service.objects.get(id=sid)
        print(f"ID: {s.id}, Name: {s.name}, Super Admin ID: {s.super_admin_service_id}")
    except Service.DoesNotExist:
        print("Service found in category but does not exist in Service table!")

if __name__ == "__main__":
    check_service()
