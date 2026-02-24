import os
import django
import sys
from datetime import datetime

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/customer_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from bookings.models import Booking

def check_latest_booking():
    print("--- Inspecting Latest Booking ---")
    try:
        latest_booking = Booking.objects.last()
        if not latest_booking:
            print("No bookings found.")
            return

        print(f"ID: {latest_booking.id}")
        print(f"Created At: {latest_booking.created_at}")
        print(f"Status: {latest_booking.status}")
        print(f"Provider ID: {latest_booking.items.first().provider_id if latest_booking.items.exists() else 'No Items'}")
        print(f"Assigned Employee: {latest_booking.items.first().assigned_employee_id if latest_booking.items.exists() else 'No Items'}")
        print(f"Pet Owner: {latest_booking.owner.user.email if latest_booking.owner and latest_booking.owner.user else 'Unknown'}")
        
        # Check items
        for item in latest_booking.items.all():
            print(f"  - Item: {item.service_name} | Date: {item.booking_date} | Status: {item.status}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_latest_booking()
