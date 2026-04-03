import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import Capability

CAPABILITIES = [
    # Veterinary Core
    {
        "key": "VETERINARY_CORE",
        "label": "Veterinary Core",
        "description": "Access to basic veterinary dashboard.",
        "group": "General"
    },
    # Reception
    {
        "key": "VETERINARY_VISITS",
        "label": "Manage Visits",
        "description": "Register patients, schedule appointments, and manage queue.",
        "group": "Reception"
    },
    {
        "key": "VETERINARY_SCHEDULE",
        "label": "Manage Schedule",
        "description": "Manage doctor schedules and availability.",
        "group": "Reception"
    },
    # Vitals / Nursing
    {
        "key": "VETERINARY_VITALS",
        "label": "Record Vitals",
        "description": "Record patient weight, temperature, pulse, etc.",
        "group": "Nursing"
    },
    # Doctor
    {
        "key": "VETERINARY_DOCTOR",
        "label": "Doctor Consultation",
        "description": "Perform diagnosis, write medical notes.",
        "group": "Doctor"
    },
    {
        "key": "VETERINARY_PRESCRIPTIONS",
        "label": "Prescribe Medicine",
        "description": "Create and manage prescriptions.",
        "group": "Doctor"
    },
    {
        "key": "VETERINARY_LABS",
        "label": "Lab Management",
        "description": "Order tests and view results.",
        "group": "Doctor"
    },
    # Pharmacy
    {
        "key": "VETERINARY_PHARMACY",
        "label": "Pharmacy",
        "description": "Dispense medicines and manage inventory.",
        "group": "Pharmacy"
    },
    {
        "key": "VETERINARY_PHARMACY_STORE",
        "label": "Pharmacy Store",
        "description": "Inventory control, batch tracking, and stock management.",
        "group": "Pharmacy"
    },
    {
        "key": "VETERINARY_MEDICINE_REMINDERS",
        "label": "Medicine Reminders",
        "description": "Send automated reminders to owners.",
        "group": "Pharmacy"
    },
    # Admin
    {
        "key": "VETERINARY_ADMIN_SETTINGS",
        "label": "Clinic Settings",
        "description": "Configure clinic metadata and settings.",
        "group": "Admin"
    },
    {
        "key": "VETERINARY_ONLINE_CONSULT",
        "label": "Online Consultancy",
        "description": "Handle virtual consultations and video calls.",
        "group": "Doctor"
    },
    {
        "key": "VETERINARY_OFFLINE_VISIT",
        "label": "Offline Visits",
        "description": "Manage walk-in and physical clinic appointments.",
        "group": "Reception"
    },
    # System / Clinic Operations
    {
        "key": "EMPLOYEE_MANAGEMENT",
        "label": "Employee Management",
        "description": "Manage clinic staff, their profiles, and assignments.",
        "group": "System"
    },
    {
        "key": "ROLE_MANAGEMENT",
        "label": "Role Management",
        "description": "Configure roles and granular access permissions.",
        "group": "System"
    },
    {
        "key": "CUSTOMER_BOOKING",
        "label": "Customer Booking Management",
        "description": "Manage online and offline customer bookings.",
        "group": "System"
    },
    {
        "key": "CLINIC_MANAGEMENT",
        "label": "Clinic Management",
        "description": "Manage clinic settings, opening hours, and metadata.",
        "group": "System"
    },
]

def seed_capabilities():
    print("🌱 Seeding Capabilities...")
    created_count = 0
    updated_count = 0
    
    for cap_data in CAPABILITIES:
        cap, created = Capability.objects.update_or_create(
            key=cap_data["key"],
            defaults={
                "label": cap_data["label"],
                "description": cap_data["description"],
                "group": cap_data["group"]
            }
        )
        status = "Created" if created else "Updated"
        if created:
            created_count += 1
        else:
            updated_count += 1
            
        print(f"   - {status}: {cap.label} ({cap.key})")

    print(f"\n✅ Seeding Complete: {created_count} Created, {updated_count} Updated.")

if __name__ == "__main__":
    seed_capabilities()
