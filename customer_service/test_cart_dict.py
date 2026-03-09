import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from carts.models import CartItem

print(list(CartItem.objects.all().order_by('-created_at').values('id', 'price_snapshot', 'created_at')[:5]))

