import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, VerifiedUser, OrganizationEmployee

def diagnose():
    print("--- Service Provider Search ---")
    providers = ServiceProvider.objects.filter(verified_user__full_name__icontains='Gopi')
    p_data = []
    for p in providers:
        p_data.append({
            "name": p.verified_user.full_name if p.verified_user else "Unknown",
            "id": str(p.id),
            "auth_user_id": str(p.verified_user.auth_user_id) if p.verified_user else None,
            "provider_type": p.provider_type
        })
    print(json.dumps(p_data, indent=2))


    print("\n--- Verified User Search ---")
    users = VerifiedUser.objects.filter(full_name__icontains='Gopi')
    u_data = []
    for u in users:
        u_data.append({
            "full_name": u.full_name,
            "auth_user_id": str(u.auth_user_id),
            "role": u.role
        })
    print(json.dumps(u_data, indent=2))

    print("\n--- Organization Employee Search (by Org ID) ---")
    # Gopi's Org Provider ID: 9c856d87-e98f-42fd-a474-dc71fc547537
    emps = OrganizationEmployee.objects.filter(organization_id='9c856d87-e98f-42fd-a474-dc71fc547537')
    e_data = []
    for e in emps:
        e_data.append({
            "full_name": e.full_name,
            "auth_user_id": str(e.auth_user_id),
            "role": e.role,
            "status": e.status
        })
    print(json.dumps(e_data, indent=2))

if __name__ == "__main__":
    diagnose()
