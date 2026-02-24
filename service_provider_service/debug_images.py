import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from provider_dynamic_fields.models import ProviderFacility, ProviderCategory

def check_facilities():
    print("--- Checking Facilities ---")
    facilities = ProviderFacility.objects.all().order_by('-created_at')[:10]
    for f in facilities:
        print(f"ID: {f.id}, Name: {f.name}, Category: {f.category.name if f.category else 'N/A'}, Image: {f.image}")
        if hasattr(f, 'gallery'):
            gallery = f.gallery.all()
            print(f"  Gallery count: {len(gallery)}")
            for img in gallery:
                print(f"    Gallery Image: {img.image}")

if __name__ == "__main__":
    check_facilities()
