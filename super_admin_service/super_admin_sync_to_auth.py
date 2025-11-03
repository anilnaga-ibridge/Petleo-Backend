import os
import django
import uuid
import requests

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from admin_core.models import SuperAdmin

# 🔹 Auth Service Base URL — update if different
AUTH_SERVICE_URL = "http://127.0.0.1:8000/api/v1/auth/register-superadmin/"  # Example endpoint

# 🔹 Root SuperAdmin details
SUPERADMIN_DATA = {
    "auth_user_id": str(uuid.uuid4()),
    "email": "root@petleo.com",
    "phone_number": "+911234567890",
    "full_name": "Root SuperAdmin",
    "role": "super_admin",
    "permissions": ["*"],  # give all permissions
}

# Step 1️⃣ Create locally in SuperAdminService
super_admin, created = SuperAdmin.objects.get_or_create(
    email=SUPERADMIN_DATA["email"],
    defaults={
        "auth_user_id": SUPERADMIN_DATA["auth_user_id"],
        "contact": SUPERADMIN_DATA["phone_number"],
        "first_name": "Root",
        "last_name": "SuperAdmin",
        "is_super_admin": True,
        "is_admin": True,
        "is_staff": True,
        "is_active": True,
        "activity_status": "active",
        "user_role": "SuperAdmin",
    },
)

if created:
    print(f"✅ Local SuperAdmin created: {super_admin.email}")
else:
    print(f"ℹ️ Local SuperAdmin already exists: {super_admin.email}")

# Step 2️⃣ Sync to Auth Service
try:
    response = requests.post(AUTH_SERVICE_URL, json=SUPERADMIN_DATA, timeout=10)

    if response.status_code in [200, 201]:
        print("✅ Synced successfully with Auth Service.")
        print("Response:", response.json())
    elif response.status_code == 409:
        print("⚠️ SuperAdmin already exists in Auth Service.")
    else:
        print(f"❌ Auth Service returned {response.status_code}: {response.text}")

except requests.exceptions.RequestException as e:
    print("🚫 Failed to connect to Auth Service:", e)
