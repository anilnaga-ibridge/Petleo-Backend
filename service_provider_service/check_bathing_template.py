import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from provider_dynamic_fields.models import ProviderTemplateCategory

def check_bathing_template():
    print("--- Checking Template Categories for Bathing ---")
    cats = ProviderTemplateCategory.objects.filter(name__icontains='Bathing')
    for c in cats:
        print(f"Template ID: {c.id}, Name: {c.name}, Service: {c.service.name if c.service else 'N/A'}")

if __name__ == "__main__":
    check_bathing_template()
