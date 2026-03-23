import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ProviderRole, ProviderRoleCapability

# Get Jhony's record
oe = OrganizationEmployee.objects.filter(email='jhony@gmail.com').first()
if not oe:
    print("Jhony not found!")
    exit()

print(f"Found: {oe.full_name} | current role={oe.role} | provider_role={oe.provider_role}")
print(f"Organization: {oe.organization}")

# Find available roles for Jhony's clinic
roles = ProviderRole.objects.filter(provider=oe.organization)
print(f"\nAvailable ProviderRoles for this clinic ({len(roles)}):")
for r in roles:
    cap_keys = list(r.capabilities.values_list('capability_key', flat=True))
    print(f"  [{r.id}] {r.name} — caps: {cap_keys}")

# Try to find a doctor role
doctor_role = roles.filter(name__icontains='doctor').first()
if not doctor_role:
    doctor_role = roles.filter(name__icontains='vet').first()

if doctor_role:
    print(f"\nAssigning role: {doctor_role.name}")
    oe.provider_role = doctor_role
    oe.role = 'doctor'
    oe.save()
    print("✅ Done! Jhony's role has been updated.")
    print(f"\nFinal permissions: {oe.get_final_permissions()}")
else:
    print("\n⚠️  No doctor/vet role found. Creating one from their current ProviderRoleCapability setup...")
    print("Please assign a ProviderRole manually or create one.")
