import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from django.core.cache import cache
from service_provider.models import OrganizationEmployee

emp = OrganizationEmployee.objects.get(email='praveen@gmail.com')
role_version = emp.provider_role.version if emp.provider_role else 0
cache_key = f"employee_perms_{emp.id}_v{role_version}"
cache.delete(cache_key)
print(f"✅ Cleared permission cache for Praveen | key: {cache_key}")

# Also try deleting without version in case old key format was used
old_key = f"employee_perms_{emp.id}"
cache.delete(old_key)
print(f"✅ Also cleared old key: {old_key}")
