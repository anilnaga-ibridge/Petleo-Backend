import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, VerifiedUser, ProviderRole

print("Checking employee for jhony...")
# Get the employee for jhony
uuid_str = '938c07c7-271c-4db7-adba-da11ac5999bd'
oe = OrganizationEmployee.objects.filter(auth_user_id=uuid_str).first()
if not oe:
    print("Could not find oe by auth_user_id. Trying VerifiedUser...")
    u = VerifiedUser.objects.filter(email='jhony@gmail.com').first()
    if u:
        oe = OrganizationEmployee.objects.filter(auth_user_id=u.auth_user_id).first()

if oe:
    print(f"Employee found! ID: {oe.id}")
    print(f"Name: {oe.full_name}, Email: {oe.email}, Legacy Role: {oe.role}")
    print(f"Provider Role: {oe.provider_role.name if oe.provider_role else 'None'}")
    if oe.provider_role:
        caps = [rc.capability_key for rc in oe.provider_role.capabilities.all()]
        print(f"Role Caps count: {len(caps)}")
        print(f"Role Caps: {caps}")
    print(f"Final Perms (from method): {oe.get_final_permissions()}")
    
    # Try the tree
    from service_provider.serializers import EmployeeMenuSerializer, EmployeeProfileSerializer
    from rest_framework.test import APIRequestFactory
    factory = APIRequestFactory()
    request = factory.get('/')
    serializer = EmployeeMenuSerializer(oe, context={'request': request})
    try:
        data = serializer.data
        if 'menu' in data:
            print("\nMenu items:")
            for m in data['menu']:
                print(m.get('name') if isinstance(m, dict) else m)
        if 'modules' in data:
            print("\nModules items:")
            for m in data['modules']:
                 print(m.get('name'))
    except Exception as e:
        print("Serializer Error:", e)

else:
    print("Could not find employee record.")
