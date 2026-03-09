
import os
import django

# Check Super Admin Service first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from admin_core.models import VerifiedUser, AdminProfile

auth_id = "87b9cb5d-ee9e-4e20-bf22-646b30b793ed"

print(f"--- Checking Super Admin Service for {auth_id} ---")
user = VerifiedUser.objects.filter(auth_user_id=auth_id).first()
if user:
    print(f"VerifiedUser found: {user.full_name}, Email: {user.email}, Avatar: {user.avatar_url}")
    profile = AdminProfile.objects.filter(verified_user=user).first()
    if profile:
        print(f"AdminProfile found: Image: {profile.profile_image}")
    else:
        print("No AdminProfile found for this user.")
else:
    print("VerifiedUser not found in Super Admin Service.")

# Reset for next service check (if needed, but usually scripts are separate)
