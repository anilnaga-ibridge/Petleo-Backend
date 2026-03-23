import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, Capability, FeatureModule
from provider_dynamic_fields.models import ProviderCapabilityAccess
from org_employees.models import OrganizationEmployee
from service_provider.utils import _build_permission_tree

# get jhony
emp = OrganizationEmployee.objects.filter(verified_user__email='jhony@gmail.com').first()
if not emp:
    print("Jhony not found")
else:
    print(f"Found Jhony: {emp.id} - Role: {emp.role.name if emp.role else 'None'}")
    
    if emp.role:
        print("Role Capabilities:", emp.role.capabilities)
            
    # Check menu explicitly
    print("\nAttempting to get menu:")
    try:
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.get('/')
        menu = _build_permission_tree(emp.verified_user, request=request)
        print("\nMenu items:")
        for m in menu:
            print(m)
    except Exception as e:
        print("Menu error:", e)

    # Let's see what modules he actually should have based on capabilities
    if emp.role:
        caps_keys = {cap.split('.')[0] for cap in emp.role.capabilities}
        modules = FeatureModule.objects.filter(capability__key__in=caps_keys, is_active=True).order_by('sequence')
        print("\nFeature Modules for these capabilities:", caps_keys)
        for m in modules:
            print(f" - {m.name} ({m.key})")
