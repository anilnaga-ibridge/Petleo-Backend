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
from veterinary.middleware import VeterinaryPermissionMiddleware
from veterinary.permissions import require_capability
from rest_framework.exceptions import PermissionDenied

def verify_capability_enforcement():
    print("\n🔹 Verifying Capability Enforcement...")

    # 1. Setup Mock Data
    auth_user_id = str(uuid.uuid4())
    clinic = Clinic.objects.create(name="Test Clinic", organization_id=str(uuid.uuid4()))
    
    # Create Staff with specific capabilities
    staff = VeterinaryStaff.objects.create(
        auth_user_id=auth_user_id,
        clinic=clinic,
        role="doctor",
        permissions=["VETERINARY_VITALS", "VETERINARY_PRESCRIPTIONS"]
    )
    print(f"   Created Staff: {staff.auth_user_id} with permissions: {staff.permissions}")

    # 2. Test Middleware
    print("   Testing Middleware...")
    middleware = VeterinaryPermissionMiddleware(get_response=lambda r: None)
    request = MagicMock()
    request.user.is_authenticated = True
    request.user.id = auth_user_id # Simulate SimpleJWT user ID
    
    middleware.process_request(request)
    
    if hasattr(request.user, 'permissions') and request.user.permissions == staff.permissions:
        print("   ✅ Middleware successfully attached permissions.")
    else:
        print(f"   ❌ Middleware FAILED. User permissions: {getattr(request.user, 'permissions', 'N/A')}")
        return

    # 3. Test Decorator
    print("   Testing @require_capability decorator...")
    
    @require_capability("VETERINARY_VITALS")
    def view_vitals(view, req):
        return "SUCCESS"

    @require_capability("VETERINARY_LABS")
    def view_labs(view, req):
        return "SUCCESS"

    # Test Allowed
    try:
        result = view_vitals(None, request)
        print(f"   ✅ Access granted for VETERINARY_VITALS: {result}")
    except PermissionDenied:
        print("   ❌ Access DENIED for VETERINARY_VITALS (Should be allowed)")

    # Test Denied
    try:
        view_labs(None, request)
        print("   ❌ Access GRANTED for VETERINARY_LABS (Should be denied)")
    except PermissionDenied:
        print("   ✅ Access properly DENIED for VETERINARY_LABS")

    # Cleanup
    staff.delete()
    clinic.delete()

if __name__ == "__main__":
    verify_capability_enforcement()
