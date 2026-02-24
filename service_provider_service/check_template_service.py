import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from provider_dynamic_fields.models import ProviderTemplateService

def check_template_service():
    sid = '8da6c82b-2136-4a14-9670-2973682107a6'
    print(f"--- Checking Template Service {sid} ---")
    try:
        s = ProviderTemplateService.objects.get(super_admin_service_id=sid)
        print(f"ID: {s.id}, Name: {s.name}, SA ID: {s.super_admin_service_id}")
    except ProviderTemplateService.DoesNotExist:
        # Maybe it's the internal ID?
        try:
             s = ProviderTemplateService.objects.get(id=sid)
             print(f"ID: {s.id}, Name: {s.name}, SA ID: {s.super_admin_service_id}")
        except:
             print("Service not found in ProviderTemplateService")

if __name__ == "__main__":
    check_template_service()
