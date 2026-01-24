
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import ServiceProvider, ProviderRole, OrganizationEmployee

def find_candidate():
    print("🔍 Looking for Organization with Custom Roles and Employees...")
    
    # Find roles with many capabilities (potential 'All-Rounder')
    roles = ProviderRole.objects.all()
    
    candidates = []
    
    for r in roles:
        cap_count = r.capabilities.count()
        emp_count = r.employees.count()
        if emp_count > 0:
            candidates.append({
                "org": r.provider.verified_user.email,
                "role": r.name,
                "cap_count": cap_count,
                "emp_count": emp_count,
                "employees": [e.auth_user_id for e in r.employees.all()]
            })

    if not candidates:
        print("❌ No suitable candidates found (Organization -> Role -> Employee chain broken).")
    else:
        print(f"✅ Found {len(candidates)} candidates:")
        for c in candidates:
            print(f" - Org: {c['org']} | Role: {c['role']} | Caps: {c['cap_count']} | Emps: {c['emp_count']}")

if __name__ == "__main__":
    find_candidate()
