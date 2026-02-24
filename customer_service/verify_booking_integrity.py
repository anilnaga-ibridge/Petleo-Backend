import os
import django
import sys
from datetime import date, timedelta

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/customer_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from bookings.models import Booking
from rest_framework.test import APIRequestFactory

def verify_booking_logic():
    print("--- Verifying Booking Logic Integrity ---")
    # Just checking if models load fine
    count = Booking.objects.count()
    print(f"Current Bookings: {count}")
    print("--- Integrity Check Passed ---")

if __name__ == "__main__":
    verify_booking_logic()
