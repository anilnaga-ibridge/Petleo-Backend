import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from carts.models import Cart, CartItem
from customers.models import PetOwnerProfile

print(f"Total Carts: {Cart.objects.count()}")
print(f"Total Cart Items: {CartItem.objects.count()}")

# Print latest 5 cart items
for item in CartItem.objects.all().order_by('-created_at')[:5]:
    owner_email = item.cart.owner.user.email if item.cart and item.cart.owner and item.cart.owner.user else 'Unknown'
    print(f"[{item.created_at}] CartItem {item.id} | Price: {item.price_snapshot} | Pet: {item.pet.name if item.pet else 'No pet'} | Svc: {item.service_id} | Owner: {owner_email}")

