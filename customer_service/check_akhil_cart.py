import os
import django
import sys

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/customer_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from carts.models import Cart, CartItem
from customers.models import PetOwnerProfile

def check_akhil_cart():
    print("--- Inspecting Cart for Akhil ---")
    try:
        # Finding profile by partial name or email if possible, or just finding the one most recently updated
        profile = PetOwnerProfile.objects.filter(full_name__icontains='Akhil').first()
        if not profile:
            print("Profile for Akhil not found. Checking all carts...")
            carts = Cart.objects.all().order_by('-updated_at')[:3]
        else:
            print(f"Found Profile: {profile.id} | Name: {profile.full_name}")
            carts = Cart.objects.filter(owner=profile)

        for cart in carts:
            print(f"Cart ID: {cart.id} | Owner: {cart.owner.full_name} | Updated: {cart.updated_at}")
            print(f"Item Count (Model): {cart.items.count()}")
            for item in cart.items.all():
                print(f"  - Item ID: {item.id}")
                print(f"    Service: {item.service_id}")
                print(f"    Facility: {item.facility_id}")
                print(f"    Price: {item.price_snapshot}")
                print(f"    Created: {item.created_at}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_akhil_cart()
