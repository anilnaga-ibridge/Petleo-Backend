import os
import django
import sys
import uuid

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider, OrganizationEmployee

def test_employee_creation():
    print("--- Testing Employee Creation Logic ---")
    
    # 1. Get Provider (nagaanil292)
    try:
        provider_user = VerifiedUser.objects.get(email='nagaanil292@gmail.com')
        print(f"Provider User: {provider_user.email} (Auth ID: {provider_user.auth_user_id})")
    except VerifiedUser.DoesNotExist:
        print("❌ User nagaanil292 not found")
        return

    try:
        provider = ServiceProvider.objects.get(verified_user=provider_user)
        print(f"Provider Profile ID: {provider.id}")
    except ServiceProvider.DoesNotExist:
        print("❌ Provider Profile NOT FOUND. Cannot proceed.")
        return

    # 2. Simulate Kafka Payload for New Employee
    new_emp_auth_id = str(uuid.uuid4())
    payload = {
        "event_type": "USER_CREATED",
        "role": "employee",
        "data": {
            "auth_user_id": new_emp_auth_id,
            "full_name": "Test Kafka Employee 2",
            "email": f"test.emp.{new_emp_auth_id[:8]}@example.com",
            "phone_number": "+1234567899",
            "organization_id": provider_user.auth_user_id, 
            "created_by": provider_user.auth_user_id
        }
    }
    
    print("\n--- Simulating Kafka Consumption ---")
    data = payload["data"]
    auth_user_id = data["auth_user_id"]
    organization_id = data["organization_id"]
    
    if not organization_id:
        print("❌ Missing organization_id")
        return

    try:
        # Logic from kafka_consumer.py
        org_provider = ServiceProvider.objects.get(
            verified_user__auth_user_id=organization_id
        )
        print(f"✅ Found Organization Provider: {org_provider.id}")
        
        emp, created = OrganizationEmployee.objects.update_or_create(
            auth_user_id=auth_user_id,
            defaults={
                "organization": org_provider,
                "full_name": data.get("full_name"),
                "email": data.get("email"),
                "phone_number": data.get("phone_number"),
                "role": "employee",
                "status": "invited",
                "created_by": data.get("created_by")
            },
        )
        print(f"✅ {'Created' if created else 'Updated'} Employee: {emp.full_name} (Org: {emp.organization.id})")
        
    except ServiceProvider.DoesNotExist:
        print(f"❌ Organization {organization_id} not found in ServiceProvider table")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_employee_creation()
