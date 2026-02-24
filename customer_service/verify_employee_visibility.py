import os
import django
from django.db.models import Q

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from bookings.models import Booking

# Tharun's Auth User ID
tharun_auth_id = "8ff9669b-aa8b-4c2e-863f-ef5420942319"

# Simulate the filtering logic in get_queryset
# is_provider will be true since the role is 'employee'
filters = Q(items__assigned_employee_id=tharun_auth_id) | Q(items__provider_id=tharun_auth_id)

queryset = Booking.objects.filter(filters).distinct()

print(f"Checking bookings for Tharun (Auth ID: {tharun_auth_id})")
print("-" * 60)
if queryset.exists():
    for b in queryset:
        item = b.items.first()
        pet_name = item.pet.name if item and item.pet else "N/A"
        service_name = item.service_snapshot.get('service_name', 'N/A') if item and item.service_snapshot else "N/A"
        print(f"Booking ID: {b.id}")
        print(f"Pet: {pet_name}")
        print(f"Service: {service_name}")
        print(f"Status: {b.status}")
        print("-" * 60)
else:
    print("No bookings found for Tharun.")
