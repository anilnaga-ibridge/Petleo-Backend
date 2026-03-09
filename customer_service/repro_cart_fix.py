
import os
import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from carts.models import Cart, CartItem
from customers.models import PetOwnerProfile
from pets.models import Pet

def test_add_doctor_consultation_to_cart():
    # 1. Get a profile
    profile = PetOwnerProfile.objects.first()
    if not profile:
        print("No profile found")
        return

    # 2. Get a pet
    pet = Pet.objects.filter(owner=profile).first()
    if not pet:
        print("No pet found for profile")
        return

    # 3. Get or create cart
    cart, _ = Cart.objects.get_or_create(owner=profile)

    # 4. Try to create CartItem with string IDs
    try:
        item = CartItem.objects.create(
            cart=cart,
            provider_id=uuid.uuid4(), # Just a dummy UUID
            pet=pet,
            service_id="2dff446f-c95f-4310-ba4d-05e3395dd7eb", # Veterinary Utility UUID
            facility_id="doctor-consultation", # THE STRING SLUG
            price_snapshot=8999.00
        )
        print(f"Successfully added item with facility_id: {item.facility_id}")
        
        # Verify it can be retrieved
        retrieved = CartItem.objects.get(id=item.id)
        print(f"Retrieved facility_id: {retrieved.facility_id}")
        
        # Cleanup
        item.delete()
        print("Test passed and cleaned up.")
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_add_doctor_consultation_to_cart()
