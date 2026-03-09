import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider, OrganizationEmployee

def search_all():
    print("--- All VerifiedUsers with 'Gopi' ---")
    users = VerifiedUser.objects.filter(full_name__icontains='Gopi')
    u_data = []
    for u in users:
        u_data.append({
            "full_name": u.full_name,
            "auth_user_id": str(u.auth_user_id),
            "role": u.role,
            "id": str(u.id)
        })
    print(json.dumps(u_data, indent=2))

    print("\n--- All OrganizationEmployees with 'Gopi' ---")
    emps = OrganizationEmployee.objects.filter(full_name__icontains='Gopi')
    e_data = []
    for e in emps:
        e_data.append({
            "full_name": e.full_name,
            "auth_user_id": str(e.auth_user_id),
            "org": e.organization.name if e.organization else None,
            "status": e.status
        })
    print(json.dumps(e_data, indent=2))

    print("\n--- Searching for specific auth_user_id from summary (c00684b3...) ---")
    u2 = VerifiedUser.objects.filter(auth_user_id='c00684b3-a4af-41ff-a24f-fa47f1a2d443').first()
    if u2:
        print(f"Found user c00684b3: {u2.full_name}, Role: {u2.role}")
    else:
        print("User c00684b3 not found.")

if __name__ == "__main__":
    search_all()
