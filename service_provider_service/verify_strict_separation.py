import os
import json
import time
import uuid
import django
from kafka import KafkaProducer

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee, ServiceProvider

# Config
KAFKA_BROKER = "localhost:9093"
TOPIC = "service_provider_events" # Both employee and individual go here in our setup? 
# Wait, individual goes to 'individual_events', employee to 'service_provider_events'
# Let's check the consumer: it listens to both.

TOPIC_EMPLOYEE = "service_provider_events"
TOPIC_INDIVIDUAL = "individual_events"

ORG_OWNER_ID = "ec23848f-dd25-4701-805d-010cbc9e10fc" # rr@gmail.com

TEST_EMP_ID = str(uuid.uuid4())
TEST_IND_ID = str(uuid.uuid4())

print(f"🧪 Starting Verification...")
print(f"   Employee ID: {TEST_EMP_ID}")
print(f"   Individual ID: {TEST_IND_ID}")
print(f"   Organization ID: {ORG_OWNER_ID}")

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def check_db(auth_id, role, step_name):
    print(f"\n🔍 Checking DB for {role} ({step_name})...")
    
    # Check OrganizationEmployee
    try:
        emp = OrganizationEmployee.objects.get(auth_user_id=auth_id)
        print(f"   ✅ Found in OrganizationEmployee: {emp.full_name} ({emp.status})")
        emp_exists = True
    except OrganizationEmployee.DoesNotExist:
        print(f"   ⚪ Not found in OrganizationEmployee")
        emp_exists = False

    # Check VerifiedUser
    try:
        user = VerifiedUser.objects.get(auth_user_id=auth_id)
        print(f"   ✅ Found in VerifiedUser: {user.full_name} ({user.role})")
        user_exists = True
    except VerifiedUser.DoesNotExist:
        print(f"   ⚪ Not found in VerifiedUser")
        user_exists = False

    return emp_exists, user_exists

# ==========================================
# TEST 1: EMPLOYEE CREATION
# ==========================================
print("\n🚀 Sending USER_CREATED for Employee...")
payload_emp = {
    "event_type": "USER_CREATED",
    "role": "employee",
    "data": {
        "auth_user_id": TEST_EMP_ID,
        "full_name": "Test Employee",
        "email": f"test.emp.{TEST_EMP_ID[:8]}@example.com",
        "phone_number": "1234567890",
        "organization_id": ORG_OWNER_ID,
        "created_by": ORG_OWNER_ID
    }
}
producer.send(TOPIC_EMPLOYEE, payload_emp)
producer.flush()
time.sleep(3) # Wait for consumer

emp_exists, user_exists = check_db(TEST_EMP_ID, "employee", "After Creation")

if emp_exists and not user_exists:
    print("   ✅ PASS: Employee created in OrgEmployee ONLY.")
else:
    print("   ❌ FAIL: Strict separation failed for Employee creation.")

# ==========================================
# TEST 2: EMPLOYEE VERIFICATION
# ==========================================
print("\n🚀 Sending USER_VERIFIED for Employee...")
payload_emp_ver = {
    "event_type": "USER_VERIFIED",
    "role": "employee",
    "data": {
        "auth_user_id": TEST_EMP_ID,
        "full_name": "Test Employee Verified",
        "email": f"test.emp.{TEST_EMP_ID[:8]}@example.com",
        "phone_number": "1234567890",
    }
}
producer.send(TOPIC_EMPLOYEE, payload_emp_ver)
producer.flush()
time.sleep(3)

emp_exists, user_exists = check_db(TEST_EMP_ID, "employee", "After Verification")
try:
    emp = OrganizationEmployee.objects.get(auth_user_id=TEST_EMP_ID)
    if emp.status == 'active':
        print("   ✅ PASS: Employee status updated to 'active'.")
    else:
        print(f"   ❌ FAIL: Employee status is {emp.status}, expected 'active'.")
except:
    pass

# ==========================================
# TEST 3: INDIVIDUAL CREATION
# ==========================================
print("\n🚀 Sending USER_CREATED for Individual...")
payload_ind = {
    "event_type": "USER_CREATED",
    "role": "individual",
    "data": {
        "auth_user_id": TEST_IND_ID,
        "full_name": "Test Individual",
        "email": f"test.ind.{TEST_IND_ID[:8]}@example.com",
        "phone_number": "0987654321",
        "role": "individual"
    }
}
producer.send(TOPIC_INDIVIDUAL, payload_ind)
producer.flush()
time.sleep(3)

emp_exists, user_exists = check_db(TEST_IND_ID, "individual", "After Creation")

if user_exists and not emp_exists:
    print("   ✅ PASS: Individual created in VerifiedUser ONLY.")
else:
    print("   ❌ FAIL: Strict separation failed for Individual creation.")

print("\n🏁 Verification Complete.")
