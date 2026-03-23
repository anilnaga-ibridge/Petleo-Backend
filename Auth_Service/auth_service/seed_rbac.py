import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_service.settings')
django.setup()

from users.models import Permission, Role

def seed_permissions():
    perms = [
        # Veterinary Service
        ('veterinary', 'veterinary.visits', 'Manage clinic visits and queue'),
        ('veterinary', 'veterinary.vitals', 'Record patient vitals'),
        ('veterinary', 'veterinary.consultation', 'Doctor consultation and notes'),
        ('veterinary', 'veterinary.prescriptions', 'Create and finalize prescriptions'),
        
        # Lab & Pharmacy
        ('lab', 'lab.workflow', 'Manage lab tests and results'),
        ('pharmacy', 'pharmacy.workflow', 'Dispense medicines and inventory'),
        
        # Billing
        ('billing', 'billing.invoices', 'Generate and view invoices'),
        
        # Reminders
        ('reminders', 'reminders.vaccinations', 'Track vaccinations and reminders'),
        ('reminders', 'reminders.deworming', 'Track deworming and reminders'),
        ('reminders', 'reminders.medicine', 'Medicine reminders'),
        ('reminders', 'reminders.followup', 'Follow-up visit reminders'),
        
        # Admin / Settings
        ('admin', 'admin.roles', 'Manage roles and permissions'),
        ('admin', 'admin.staff', 'Manage clinic staff assignments'),
    ]

    for service_name, capability_key, description in perms:
        Permission.objects.update_or_create(
            capability_key=capability_key,
            defaults={
                'service_name': service_name,
                'description': description
            }
        )
    print(f"Successfully seeded {len(perms)} permissions.")

def seed_role_templates():
    from users.models import RolePermission, Role, Permission
    
    templates = [
        ("Clinic Admin", "Full access to all clinic modules", [
            ('veterinary.visits', ['view', 'create', 'edit', 'delete']),
            ('veterinary.vitals', ['view', 'create', 'edit', 'delete']),
            ('veterinary.consultation', ['view', 'create', 'edit', 'delete']),
            ('veterinary.prescriptions', ['view', 'create', 'edit', 'delete']),
            ('lab.workflow', ['view', 'create', 'edit', 'delete']),
            ('pharmacy.workflow', ['view', 'create', 'edit', 'delete']),
            ('billing.invoices', ['view', 'create', 'edit', 'delete']),
            ('reminders.vaccinations', ['view', 'create', 'edit', 'delete']),
            ('reminders.deworming', ['view', 'create', 'edit', 'delete']),
            ('reminders.medicine', ['view', 'create', 'edit', 'delete']),
            ('reminders.followup', ['view', 'create', 'edit', 'delete']),
            ('admin.roles', ['view', 'create', 'edit', 'delete']),
            ('admin.staff', ['view', 'create', 'edit', 'delete']),
        ]),
        ("Doctor", "Veterinary consultation and medical records", [
            ('veterinary.visits', ['view', 'edit']),
            ('veterinary.vitals', ['view', 'create', 'edit']),
            ('veterinary.consultation', ['view', 'create', 'edit']),
            ('veterinary.prescriptions', ['view', 'create', 'edit']),
            ('lab.workflow', ['view', 'create']),
            ('pharmacy.workflow', ['view']),
            ('reminders.vaccinations', ['view', 'create', 'edit']),
            ('reminders.deworming', ['view', 'create', 'edit']),
        ]),
        ("Receptionist", "Appointment management and billing", [
            ('veterinary.visits', ['view', 'create', 'edit']),
            ('veterinary.vitals', ['view']),
            ('billing.invoices', ['view', 'create', 'edit']),
            ('reminders.followup', ['view', 'create', 'edit']),
        ]),
    ]
    
    for name, desc, perms_list in templates:
        role, _ = Role.objects.update_or_create(
            clinic_id=None,
            name=name,
            defaults={'description': desc}
        )
        # Clear and re-set perms for template
        RolePermission.objects.filter(role=role).delete()
        for cap_key, actions in perms_list:
            try:
                permission = Permission.objects.get(capability_key=cap_key)
                RolePermission.objects.create(
                    role=role,
                    permission=permission,
                    can_view='view' in actions,
                    can_create='create' in actions,
                    can_edit='edit' in actions,
                    can_delete='delete' in actions
                )
            except Permission.DoesNotExist:
                pass
    print(f"Successfully seeded {len(templates)} role templates.")

if __name__ == '__main__':
    seed_permissions()
    seed_role_templates()
