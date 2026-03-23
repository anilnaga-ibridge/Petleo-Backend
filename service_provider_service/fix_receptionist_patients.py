import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ProviderRole, ProviderRoleCapability, OrganizationEmployee
from service_provider.kafka_producer import publish_employee_updated
from django.core.cache import cache

roles = ProviderRole.objects.filter(name__icontains='reception')
for role in roles:
    has_patients = role.capabilities.filter(capability_key='VETERINARY_PATIENTS').exists()
    if not has_patients:
        ProviderRoleCapability.objects.create(
            provider_role=role,
            capability_key='VETERINARY_PATIENTS',
            can_view=True,
            can_create=True,
            can_edit=True,
            can_delete=False
        )
        print(f"Added VETERINARY_PATIENTS to {role.name} for org {role.provider.id}")
        
    # Increment version to bust cache
    role.version += 1
    role.save()
        
emps = OrganizationEmployee.objects.filter(provider_role__in=roles)
for emp in emps:
    # also explicitly clear cache just in case
    cache_key = f"employee_perms_{emp.id}_v{role.version - 1}"
    cache.delete(cache_key)
    publish_employee_updated(emp)
    print(f"Synced employee {emp.full_name} to update permissions")
