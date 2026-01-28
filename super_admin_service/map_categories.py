
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from dynamic_categories.models import Category
from dynamic_services.models import Service

print("Mapping Categories to Capabilities for VETERINARY_CORE:")
svc = Service.objects.filter(name="VETERINARY_CORE").first()
if svc:
    cats = Category.objects.filter(service=svc)
    for c in cats:
        print(f"Category: {c.name} -> Capability: {c.linked_capability}")
else:
    print("Service VETERINARY_CORE not found.")
