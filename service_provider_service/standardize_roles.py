import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee

def fix_roles():
    org_id = '19b55dd4-c2bb-474c-b5bf-d39077f52dfe' # Dhatha
    emps = OrganizationEmployee.objects.filter(organization_id=org_id)
    count = 0
    for e in emps:
        if e.role != 'employee':
            print(f"Updating {e.full_name}: {e.role} -> employee")
            e.role = 'employee'
            e.save()
            count += 1
    print(f"✅ Fixed {count} employee type records in service_provider_service.")

if __name__ == "__main__":
    fix_roles()
