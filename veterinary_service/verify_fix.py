import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from django.contrib.auth import get_user_model
from veterinary.models import StaffClinicAssignment

User = get_user_model()
org_uuid = "87b9cb5d-ee9e-4e20-bf22-646b30b793ed"

user = User.objects.filter(username=org_uuid).first()
if not user:
    print("User not found!")
else:
    print(f"user.id (int PK) = {user.id}")
    print(f"user.username (UUID) = {user.username}")
    
    # Old buggy way
    qs_old = StaffClinicAssignment.objects.filter(clinic__organization_id=str(user.id))
    print(f"\n[OLD BUG] filter by user.id={user.id} -> count = {qs_old.count()}")
    
    # New correct way
    qs_new = StaffClinicAssignment.objects.filter(clinic__organization_id=str(user.username))
    print(f"[FIXED]   filter by user.username={user.username} -> count = {qs_new.count()}")
    
    for a in qs_new:
        print(f"  - {a.staff.auth_user_id} -> {a.clinic.name}")
