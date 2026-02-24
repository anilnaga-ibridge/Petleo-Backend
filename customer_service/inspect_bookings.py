import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from bookings.models import Booking, BookingItem

bookings = BookingItem.objects.all().order_by('-id')[:5]
print(f"{'ID':<5} | {'Pet':<15} | {'Service':<20} | {'Employee ID':<36} | {'Status':<10}")
print("-" * 100)
for b in bookings:
    pet_name = b.pet.name if b.pet else "N/A"
    snapshot = b.service_snapshot or {}
    print(f"{str(b.id):<36} | {pet_name:<15} | {snapshot.get('service_name', 'N/A'):<20} | {str(b.assigned_employee_id):<36} | {b.status:<10}")
