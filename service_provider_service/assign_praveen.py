import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ProviderRole
from django.db import transaction

# Get Praveen
try:
    praveen = OrganizationEmployee.objects.get(full_name__icontains='Praveen')
    receptionist_role = ProviderRole.objects.filter(name__icontains='Receptionist').first()
    
    if receptionist_role:
        praveen.provider_role = receptionist_role
        praveen.save()
        print(f"✅ Assigned {receptionist_role.name} to {praveen.full_name}")
        
        # Test final permissions
        perms = praveen.get_final_permissions()
        print(f"Final Permissions: {perms}")
        
        # Trigger Kafka update manually if needed
        from service_provider.kafka_producer import publish_employee_updated
        publish_employee_updated(praveen)
        print("Kafka event sent!")
    else:
        print("Receptionist role not found")
except Exception as e:
    print(f"Error: {e}")
