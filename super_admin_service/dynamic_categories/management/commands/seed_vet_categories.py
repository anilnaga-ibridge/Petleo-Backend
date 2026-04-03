from django.core.management.base import BaseCommand
from dynamic_services.models import Service
from dynamic_categories.models import Category
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Seed Veterinary system categories'

    def handle(self, *args, **options):
        self.stdout.write("--- Seeding Veterinary System Categories ---")

        # 1. Ensure Veterinary Service exists
        service, created = Service.objects.get_or_create(
            name="VETERINARY",
            defaults={
                'display_name': "Veterinary Management",
                'description': "Complete veterinary practice management",
                'icon': "tabler-stethoscope"
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created Service: {service.name}"))
        else:
            self.stdout.write(f"Service exists: {service.name}")

        # 2. Define System Categories
        system_categories = [
            {
                "name": "Reception Desk",
                "category_key": "VETERINARY_VISITS",
                "description": "Register pets, create visits, and check patients in"
            },
            {
                "name": "Nurse Station",
                "category_key": "VETERINARY_VITALS",
                "description": "Record temperature, weight, and basic health indicators"
            },
            {
                "name": "Doctor Consultation",
                "category_key": "VETERINARY_DOCTOR",
                "description": "Diagnose patients and prescribe medications"
            },
            {
                "name": "Laboratory",
                "category_key": "VETERINARY_LABS",
                "description": "Order and upload lab test results"
            },
            {
                "name": "Pharmacy",
                "category_key": "VETERINARY_PHARMACY",
                "description": "Dispense medicines and complete visits"
            }
        ]

        for cat_data in system_categories:
            category, created = Category.objects.get_or_create(
                service=service,
                category_key=cat_data["category_key"],
                defaults={
                    "name": cat_data["name"],
                    "description": cat_data["description"],
                    "is_system": True,
                    "is_active": True,
                    "value": slugify(cat_data["name"]).replace("-", "_")
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created System Category: {category.name}"))
            else:
                # Ensure it's marked as system if it already exists
                if not category.is_system:
                    category.is_system = True
                    category.save()
                    self.stdout.write(self.style.WARNING(f"Updated existing category to System: {category.name}"))
                else:
                    self.stdout.write(f"System Category exists: {category.name}")

        self.stdout.write(self.style.SUCCESS("--- Seeding Complete ---"))
