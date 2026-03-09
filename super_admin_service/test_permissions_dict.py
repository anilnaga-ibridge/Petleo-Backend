import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from plans_coupens.models import PlanCapability

cap = PlanCapability.objects.filter(permissions__isnull=False).first()
if cap:
    print(f"Cap permissions: {cap.permissions}")
    print(f"Type: {type(cap.permissions)}")
    print(f"can_edit: {cap.permissions.get('can_edit', False)}")
else:
    print("No capability found")
