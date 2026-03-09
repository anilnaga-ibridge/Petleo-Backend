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

    from dynamic_categories.models import Capability

    # 2. Backward Compatibility: Still create core categories if needed, or we can just seed Capabilities
    # The prompt explicitly says: "Persist granular capabilities instead of broad ones. Group them logically by module."

    granular_capabilities = [
        # Appointments Module
        ("appointment.create", "appointments", "Create new appointments"),
        ("appointment.update", "appointments", "Modify or reschedule appointments"),
        ("appointment.cancel", "appointments", "Cancel appointments"),
        ("appointment.view",   "appointments", "View appointment calendar"),
        
        # Consultation Module
        ("consultation.create", "consultation", "Start a new patient consultation"),
        ("consultation.update", "consultation", "Update ongoing consultation details"),
        ("consultation.view",   "consultation", "View past and present consultations"),
        
        # Vitals Module
        ("vitals.create", "vitals", "Record new patient vitals (Check-in)"),
        ("vitals.update", "vitals", "Update existing vitals records"),
        ("vitals.view",   "vitals", "View patient vitals history"),
        
        # Lab Module
        ("lab.order",         "lab", "Order new lab tests"),
        ("lab.queue.view",    "lab", "View pending laboratory queues"),
        ("lab.report.upload", "lab", "Upload completed test reports"),
        ("lab.status.update", "lab", "Change lap processing status"),
        
        # Prescription & Pharmacy Module
        ("prescription.create", "pharmacy", "Write dynamic prescriptions"),
        ("prescription.view",   "pharmacy", "View prescription history"),
        ("medicine.dispense",   "pharmacy", "Dispense physical medicines"),
        ("inventory.update",    "pharmacy", "Adjust pharmacy inventory"),
        ("stock.view",          "pharmacy", "View pharmacy stock levels"),
        
        # Vaccination Module
        ("vaccination.schedule",   "vaccination", "Schedule future vaccinations"),
        ("vaccination.administer", "vaccination", "Administer and log given vaccines"),
        ("vaccination.view",       "vaccination", "View patient vaccination history"),
        ("vaccination.stock.view", "vaccination", "View vaccine inventory levels"),
        
        # Billing Module
        ("invoice.generate", "billing", "Generate invoices from clinical work"),
        ("payment.collect",  "billing", "Process and collect payments"),
        ("payment.view",     "billing", "View billing history and receipts"),
        
        # Reminder Module
        ("reminder.view",          "reminder", "View scheduled reminders"),
        ("reminder.trigger",       "reminder", "Manually trigger reminders via SMS/Email"),
        ("reminder.template.edit", "reminder", "Edit reminder message templates"),
        
        # Analytics Module
        ("analytics.view", "analytics", "View clinic financial and operational metrics"),
    ]

    print("Seeding granular capabilities...")
    for code, module, desc in granular_capabilities:
        cap, created = Capability.objects.get_or_create(
            code=code,
            defaults={
                'service': service,
                'module': module,
                'description': desc,
                'version': "1.0",
                'is_active': True
            }
        )
        print(f"  - Capability (v{cap.version}): {cap.code} [{cap.module}] ({'Created' if created else 'Exists'})")

    print("Done.")

if __name__ == '__main__':
    create_capabilities()
