import os
import django
import sys

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/customer_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from customers.models import PetOwnerProfile
from carts.models import Cart

def cleanup_profiles():
    print("--- Cleaning up duplicate profiles ---")
    # Akhil's correct profile ID: c22b41ba-6d26-40c9-893e-a3752677e9f8
    # The wrong profile ID found in logs: 070a3f8f-527c-41c0-87db-9d8bc133575b
    
    wrong_profile_id = '070a3f8f-527c-41c0-87db-9d8bc133575b'
    try:
        profile = PetOwnerProfile.objects.filter(id=wrong_profile_id).first()
        if profile:
            print(f"Deleting wrong profile: {profile.id} (auth_user_id: {profile.auth_user_id})")
            # Carts and Items should cascade if defined, but let's be sure
            Cart.objects.filter(owner=profile).delete()
            profile.delete()
            print("Successfully deleted.")
        else:
            print("Wrong profile not found or already deleted.")
            
        # General check: Find profiles where auth_user_id matches an existing profile's ID
        profile_ids = PetOwnerProfile.objects.values_list('id', flat=True)
        suspects = PetOwnerProfile.objects.filter(auth_user_id__in=profile_ids)
        for s in suspects:
            print(f"Suspect found: {s.id} | auth_user_id: {s.auth_user_id}")
            if str(s.id) != str(s.auth_user_id): # Just in case
                 print(f"  -> Deleting suspect profile {s.id}")
                 Cart.objects.filter(owner=s).delete()
                 s.delete()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    cleanup_profiles()
