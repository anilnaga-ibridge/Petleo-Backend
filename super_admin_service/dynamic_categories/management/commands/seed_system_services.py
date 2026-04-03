from django.core.management.base import BaseCommand
from dynamic_services.models import Service
from dynamic_categories.models import Category
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Seed System Management service and categories'

    def handle(self, *args, **options):
        self.stdout.write("--- Seeding System Management Service & Categories ---")

        # 1. Ensure System Service exists
        service, created = Service.objects.get_or_create(
            name="SYSTEM_ADMIN",
            defaults={
                'display_name': "System Management",
                'description': "Global clinic operations and administrative controls",
                'icon': "tabler-settings"
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created Service: {service.name}"))
        else:
            self.stdout.write(f"Service exists: {service.name}")

        # 2. Define System Categories
        system_categories = [
            {
                "name": "Employee Management",
                "category_key": "EMPLOYEE_MANAGEMENT",
                "description": "Manage clinic staff, profiles, and assignments"
            },
            {
                "name": "Role Management",
                "category_key": "ROLE_MANAGEMENT",
                "description": "Configure roles and granular access permissions"
            },
            {
                "name": "Customer Booking Management",
                "category_key": "CUSTOMER_BOOKING",
                "description": "Manage online and offline customer bookings"
            },
            {
                "name": "Clinic Management",
                "category_key": "CLINIC_MANAGEMENT",
                "description": "Manage clinic settings, opening hours, and metadata"
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
                self.stdout.write(f"System Category exists: {category.name}")

        self.stdout.write(self.style.SUCCESS("--- Seeding Complete ---"))
