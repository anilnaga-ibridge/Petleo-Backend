import os
import sys
import django
import uuid
from unittest.mock import MagicMock

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/veterinary_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import VeterinaryStaff, Clinic
from veterinary.permissions import require_capability
from rest_framework.exceptions import PermissionDenied

def test_granular_permissions():
    print("\n🚀 Verifying Granular RBAC Enforcement...")

    # 1. Setup Mock User with Granular Permissions
    auth_user_id = str(uuid.uuid4())
    request = MagicMock()
    request.user.is_authenticated = True
    request.user.id = auth_user_id
    request.user.role = "DOCTOR"
    
    # CASE 1: Direct Match
    print("\n   [CASE 1] Testing Direct Match ('vitals.create')...")
    request.user.permissions = ["vitals.create", "consultation.view"]
    
    @require_capability("vitals.create")
    def create_vitals(view, req): return "ALLOWED"
    
    try:
        res = create_vitals(None, request)
        print(f"      ✅ Success: {res}")
    except PermissionDenied as e:
        print(f"      ❌ FAILED: {e}")

    # CASE 2: Wildcard Match
    print("\n   [CASE 2] Testing Wildcard Match ('vitals.*' -> 'vitals.create')...")
    request.user.permissions = ["vitals.*", "consultation.view"]
    
    try:
        res = create_vitals(None, request)
        print(f"      ✅ Success: {res}")
    except PermissionDenied as e:
        print(f"      ❌ FAILED: {e}")

    # CASE 3: Permission Denied (Wrong Action)
    print("\n   [CASE 3] Testing Action Mismatch ('vitals.view' -> 'vitals.create')...")
    request.user.permissions = ["vitals.view"]
    
    try:
        create_vitals(None, request)
        print("      ❌ FAILED: Access granted incorrectly")
    except PermissionDenied:
        print("      ✅ Success: Access properly denied")

    # CASE 4: Permission Denied (Wrong Module)
    print("\n   [CASE 4] Testing Module Mismatch ('lab.*' -> 'vitals.create')...")
    request.user.permissions = ["lab.*"]
    
    try:
        create_vitals(None, request)
        print("      ❌ FAILED: Access granted incorrectly")
    except PermissionDenied:
        print("      ✅ Success: Access properly denied")

    # CASE 5: Legacy Owner Role (Senior Dev Safety Net)
    print("\n   [CASE 5] Testing Legacy Owner Role (Automatic Full Suite)...")
    request.user.role = "ORGANIZATION"
    request.user.permissions = None # Simulate missing sync
    
    @require_capability("lab.queue.view")
    def view_labs(view, req): return "ALLOWED"
    
    try:
        # The decorator should auto-populate permissions for Owners/Admins
        res = view_labs(None, request)
        print(f"      ✅ Success: {res}")
        print(f"      💡 Populated Perms: {request.user.permissions}")
    except PermissionDenied as e:
        print(f"      ❌ FAILED: {e}")

    print("\n✅ Verification Complete!")

if __name__ == "__main__":
    test_granular_permissions()
