
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from dynamic_services.models import Service

# Find the VETERINARY service
svc = Service.objects.filter(name__iexact="VETERINARY").first()

if svc:
    print(f"Found Service: {svc.name} (ID: {svc.id})")
    print(f"Display Name: {svc.display_name}")
    
    # Rename key to VETERINARY_CORE
    svc.name = "VETERINARY_CORE"
    # svc.display_name = "Veterinary Core" # Optional, keep display name if good
    svc.save()
    print("Successfully renamed Service to VETERINARY_CORE")
else:
    print("Service 'VETERINARY' not found. Checking if VETERINARY_CORE already exists...")
    core = Service.objects.filter(name__iexact="VETERINARY_CORE").first()
    if core:
        print(f"VETERINARY_CORE already exists: {core.id}")
    else:
        print("No Veterinary service found at all.")
