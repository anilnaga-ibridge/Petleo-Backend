
import os
import sys
import django

# Setup Django for Service Provider Service
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import OrganizationEmployee, ProviderRole, ProviderRoleCapability, ServiceProvider

# Role templates matching LEGACY_ROLE_MAP
ROLE_TEMPLATES = {
    "receptionist": {
        "capabilities": ["VETERINARY_CORE", "VETERINARY_VISITS"],
        "description": "Front desk staff managing appointments and patient check-in"
    },
    "vitals staff": {
        "capabilities": ["VETERINARY_CORE", "VETERINARY_VITALS"],
        "description": "Staff responsible for recording patient vitals"
    },
    "doctor": {
        "capabilities": ["VETERINARY_CORE", "VETERINARY_VISITS", "VETERINARY_VITALS", 
                        "VETERINARY_PRESCRIPTIONS", "VETERINARY_LABS"],
        "description": "Medical doctor with full clinical access"
    },
    "lab tech": {
        "capabilities": ["VETERINARY_CORE", "VETERINARY_LABS"],
        "description": "Laboratory technician managing test orders and results"
    },
    "pharmacy": {
        "capabilities": ["VETERINARY_CORE", "VETERINARY_MEDICINE_REMINDERS"],
        "description": "Pharmacy staff managing prescriptions and medicine reminders"
    },
    "employee": {
        "capabilities": ["VETERINARY_CORE"],
        "description": "Basic employee with core access only"
    }
}

def migrate_employee_to_provider_role(employee, dry_run=True):
    """
    Migrate a single employee from legacy role string to ProviderRole.
    """
    if employee.provider_role:
        return None, "Already has ProviderRole"
    
    # Get legacy role
    legacy_role = (employee.role or "employee").lower()
    template = ROLE_TEMPLATES.get(legacy_role)
    
    if not template:
        return None, f"Unknown legacy role: {legacy_role}"
    
    # Create role name (title case)
    role_name = employee.role.title() if employee.role else "Employee"
    
    if dry_run:
        return {
            "employee_id": employee.id,
            "employee_email": employee.auth_user_id,
            "legacy_role": legacy_role,
            "new_role_name": role_name,
            "capabilities": template["capabilities"]
        }, "Would create"
    
    # Create or get ProviderRole for this organization
    # Note: ProviderRole is linked to ServiceProvider (organization), not VerifiedUser
    role, created = ProviderRole.objects.get_or_create(
        provider=employee.organization,
        name=role_name,
        defaults={
            "description": template["description"]
        }
    )
    
    # Add capabilities if role was just created
    if created:
        for cap_key in template["capabilities"]:
            ProviderRoleCapability.objects.create(
                provider_role=role,
                capability_key=cap_key
            )
    
    # Assign role to employee
    employee.provider_role = role
    employee.save()
    
    return {
        "employee_id": employee.id,
        "employee_email": employee.auth_user_id,
        "legacy_role": legacy_role,
        "new_role": role.name,
        "role_created": created,
        "capabilities": list(role.capabilities.values_list('key', flat=True))
    }, "Migrated"

def migrate_all_employees(dry_run=True):
    """
    Migrate all employees without provider_role to database-driven roles.
    """
    print("=" * 80)
    print("EMPLOYEE LEGACY ROLE MIGRATION")
    print("=" * 80)
    print()
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    else:
        print("⚠️  LIVE MODE - Changes will be saved to database")
    print()
    
    # Find all employees without provider_role
    legacy_employees = OrganizationEmployee.objects.filter(provider_role__isnull=True)
    total = legacy_employees.count()
    
    print(f"Found {total} employees using legacy roles\n")
    
    if total == 0:
        print("✅ All employees already migrated!")
        return
    
    # Group by organization for better reporting
    orgs = {}
    for emp in legacy_employees:
        org_name = emp.organization.verified_user.full_name
        if org_name not in orgs:
            orgs[org_name] = []
        orgs[org_name].append(emp)
    
    # Migrate by organization
    migrated_count = 0
    error_count = 0
    
    for org_name, employees in orgs.items():
        print(f"\n📋 Organization: {org_name}")
        print(f"   Employees to migrate: {len(employees)}")
        print()
        
        for emp in employees:
            result, status = migrate_employee_to_provider_role(emp, dry_run)
            
            if result:
                migrated_count += 1
                print(f"  ✅ {status}: {result['employee_email']}")
                print(f"     Legacy: {result['legacy_role']} → New: {result.get('new_role_name', result.get('new_role'))}")
                print(f"     Capabilities: {', '.join(result['capabilities'])}")
            else:
                error_count += 1
                print(f"  ❌ Error: {status}")
    
    print()
    print("=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"Total employees: {total}")
    print(f"Successfully migrated: {migrated_count}")
    print(f"Errors: {error_count}")
    
    if dry_run:
        print()
        print("ℹ️  This was a dry run. Run with --run flag to apply changes.")
    else:
        print()
        print("✅ Migration complete!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate employees from legacy roles to ProviderRole')
    parser.add_argument('--run', action='store_true', help='Actually perform migration (default is dry-run)')
    
    args = parser.parse_args()
    
    migrate_all_employees(dry_run=not args.run)
