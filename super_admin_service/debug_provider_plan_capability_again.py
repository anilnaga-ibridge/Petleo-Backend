import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from plans_coupens.models import ProviderPlanCapability
from users.models import User

# Find the user
user = User.objects.filter(email__icontains='anil').first()
if not user:
    print("Could not find user")
    exit()

print(f"User: {user.email}")

caps = ProviderPlanCapability.objects.filter(user=user)
print(f"Total ProviderPlanCapability: {caps.count()}")

for cap in caps:
    svc_name = cap.service.display_name if cap.service else 'None'
    cat_name = cap.category.name if cap.category else 'None'
    fac_name = cap.facility.name if cap.facility else 'None'
    print(f"  Permissions: {cap.permissions}")
    print(f"Svc: {svc_name}, Cat: {cat_name}, Fac: {fac_name}")

