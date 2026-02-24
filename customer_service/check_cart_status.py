import os
import django
import sys

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/customer_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from carts.models import Cart, CartItem

def check_cart():
    print("--- Inspecting Carts ---")
    carts = Cart.objects.all().order_by('-updated_at')[:5]
    for cart in carts:
        print(f"Cart ID: {cart.id} | Owner: {cart.owner.id if cart.owner else 'None'} | Updated: {cart.updated_at}")
        for item in cart.items.all():
            print(f"  - Item: {item.service_id} | Provider: {item.provider_id} | Price: {item.price_snapshot}")

if __name__ == "__main__":
    check_cart()
