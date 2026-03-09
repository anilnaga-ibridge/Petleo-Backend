from django.core.management.base import BaseCommand
from org_employees.models import OrganizationRole

class Command(BaseCommand):
    help = 'Seed default system role templates with granular module.action capability codes'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding default role templates...")

        templates = {
            "Doctor": [
                "consultation.create", "consultation.update", "consultation.view",
                "lab.order", "prescription.create", "vaccination.administer",
                "appointment.create", "appointment.view"
            ],
            "Receptionist": [
                "appointment.create", "appointment.update", "appointment.cancel", "appointment.view",
                "vitals.create", # Patient check-in
                "invoice.generate", "payment.collect", "payment.view"
            ],
            "Vitals Staff": [
                "vitals.create", "vitals.update", "vitals.view"
            ],
            "Lab Technician": [
                "lab.queue.view", "lab.report.upload", "lab.status.update"
            ],
            "Pharmacist": [
                "prescription.view", "medicine.dispense", "inventory.update", "stock.view"
            ],
            "Reminder Staff": [
                "reminder.view", "reminder.trigger", "reminder.template.edit"
            ],
            "Vaccination Staff": [
                "vaccination.schedule", "vaccination.administer", "vaccination.view", "vaccination.stock.view"
            ],
            "Clinic Admin": [
                "appointment.create", "appointment.update", "appointment.cancel", "appointment.view",
                "consultation.create", "consultation.update", "consultation.view",
                "vitals.create", "vitals.update", "vitals.view",
                "lab.order", "lab.queue.view", "lab.report.upload", "lab.status.update",
                "prescription.create", "prescription.view", "medicine.dispense", "inventory.update", "stock.view",
                "vaccination.schedule", "vaccination.administer", "vaccination.view", "vaccination.stock.view",
                "invoice.generate", "payment.collect", "payment.view",
                "reminder.view", "reminder.trigger", "reminder.template.edit",
                "analytics.view"
            ]
        }

        for role_name, caps in templates.items():
            role, created = OrganizationRole.objects.get_or_create(
                name=role_name,
                organization__isnull=True, # System templates belong to no specific org
                defaults={
                    'capabilities': caps,
                    'is_system': True
                }
            )
            
            if not created:
                # Update existing system roles with new capabilities if needed
                role.capabilities = caps
                role.save()
            
            self.stdout.write(self.style.SUCCESS(f"  - Role Template: {role.name} ({len(caps)} capabilities)"))

        self.stdout.write(self.style.SUCCESS('Successfully seeded role templates!'))
