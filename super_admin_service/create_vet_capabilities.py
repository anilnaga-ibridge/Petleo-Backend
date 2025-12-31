import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from dynamic_services.models import Service
from dynamic_categories.models import Category

def create_capabilities():
    print("Creating Veterinary Capabilities...")

    # 1. Create Service
    service, created = Service.objects.get_or_create(
        name="VETERINARY",
        defaults={
            'display_name': "Veterinary Management",
            'description': "Complete veterinary practice management",
            'icon': "tabler-stethoscope"
        }
    )
    print(f"Service: {service.display_name} ({'Created' if created else 'Exists'})")

    # 2. Create Categories (Capabilities)
    categories = [
        ("VETERINARY_CORE", "Core Access", "Basic access to veterinary module"),
        ("VETERINARY_VISITS", "Visits Management", "Manage patient visits"),
        ("VETERINARY_VITALS", "Vitals Recording", "Record patient vitals"),
        ("VETERINARY_PRESCRIPTIONS", "Prescriptions", "Manage prescriptions"),
        ("VETERINARY_LABS", "Lab Management", "Manage lab tests and results"),
        ("VETERINARY_ONLINE_CONSULT", "Online Consult", "Telemedicine features"),
        ("VETERINARY_OFFLINE_VISIT", "Offline Visit", "In-clinic visit management"),
        ("VETERINARY_MEDICINE_REMINDERS", "Medicine Reminders", "Automated reminders"),
    ]

    for code, name, desc in categories:
        cat, created = Category.objects.get_or_create(
            name=code,
            service=service,
            defaults={
                'description': desc,
                'is_active': True
            }
        )
        print(f"  - Category: {cat.name} ({'Created' if created else 'Exists'})")

    print("Done.")

if __name__ == '__main__':
    create_capabilities()
