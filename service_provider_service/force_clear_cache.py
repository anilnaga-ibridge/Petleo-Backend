import os
import django
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from django.core.cache import cache
from service_provider.models import OrganizationEmployee

def clear_all_employee_permissions_cache():
    print("🧹 Starting full permission cache clear...")
    
    # 1. Clear by known pattern
    # The key pattern is employee_perms_{id}_{role_id}_v{version}
    # Since we can't easily glob Redis from here (if using Redis), we'll do it for all employees
    
    employees = OrganizationEmployee.objects.all()
    count = 0
    for emp in employees:
        # We try both with and without role_id just in case
        role_id = emp.role_id if hasattr(emp, 'role_id') else 'None'
        
        keys = [
            f"employee_perms_{emp.id}_{role_id}_v1",
            f"employee_perms_{emp.id}_{role_id}_v2",
            f"employee_perms_{emp.id}_None_v1",
            f"employee_perms_{emp.id}_None_v2"
        ]
        
        for k in keys:
            cache.delete(k)
        count += 1
    
    # 2. Hard clear (if using default cache)
    cache.clear()
    
    print(f"✅ Cleared cache for {count} employees and performed global cache.clear()")

if __name__ == "__main__":
    clear_all_employee_permissions_cache()
