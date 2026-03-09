import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from carts.models import CartItem

items = CartItem.objects.all().order_by('-created_at')[:5]
for item in items:
    print(f"[{item.created_at}] ID: {item.id}, Svc: {item.service_id}, Price: {item.price_snapshot}")

