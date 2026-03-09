import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import ServiceProvider, ProviderRole
from service_provider.serializers import ProviderRoleSerializer

provider = ServiceProvider.objects.first()

data = {
    "name": "Test Role Script",
    "description": "A test role",
    "capabilities": ["VETERINARY_VITALS"]
}

# Create a mock context if needed, but serializer might not strictly need request
serializer = ProviderRoleSerializer(data=data)
if serializer.is_valid():
    print("Serializer is valid!")
    try:
        role = serializer.save(provider=provider)
        print(f"Role created: {role}")
        print("Data representation:")
        print(serializer.data)
        
        # Test serialization of existing role
        print("Testing read of existing role...")
        read_serializer = ProviderRoleSerializer(role)
        print(read_serializer.data)
        
        # Clean up
        role.delete()
        print("Test role cleaned up.")
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print("Serializer errors:", serializer.errors)
