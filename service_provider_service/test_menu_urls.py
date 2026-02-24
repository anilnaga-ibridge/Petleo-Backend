import os
import django
import sys
from unittest.mock import MagicMock

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider
from service_provider.utils import _build_permission_tree

def test_menu_urls():
    print("--- Testing Menu URLs ---")
    provider = ServiceProvider.objects.first()
    if not provider:
        print("No provider found")
        return

    # Mock request
    request = MagicMock()
    request.build_absolute_uri.side_effect = lambda url: f"http://127.0.0.1:8002{url}"

    menu = _build_permission_tree(provider.verified_user, request=request)
    
    for svc in menu:
        print(f"Service: {svc.get('service_name', svc.get('name'))}")
        categories = svc.get('categories', [])
        for cat in categories:
            print(f"  Category: {cat.get('category_name', cat.get('name'))}")
            facilities = cat.get('facilities', [])
            for fac in facilities:
                print(f"    Facility: {fac.get('facility_name', fac.get('name'))}, Image: {fac.get('image_url')}")
                if fac.get('gallery'):
                    print(f"      Gallery: {fac.get('gallery')}")

if __name__ == "__main__":
    test_menu_urls()
