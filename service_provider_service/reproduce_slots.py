import os
import django
import sys
from datetime import date

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.services.availability_service import AvailabilityService

# Rahul's Auth ID
RAHUL_AUTH_ID = '5c3b54b9-aa99-441d-8598-df3aea0b59fd'
TARGET_DATE = date(2026, 2, 26)

print(f"Testing slot generation for {TARGET_DATE}...")

# Test with 60 min duration (default)
slots_60 = AvailabilityService.get_available_slots(RAHUL_AUTH_ID, None, TARGET_DATE)
print(f"Slots (60 min duration): {slots_60}")

# Test with 30 min duration
# We can't easily pass duration without a facility_id unless we mock it, 
# but we can see the logic in availability_service.py.
# If no facility_id is passed, it uses 60.

print("\nLogic check:")
print("Shift: 09:00 - 19:00")
print("Duration: 60 mins")
print("Last slot starting at 18:00 ends at 19:00 (Fits)")
print("Next slot starting at 18:15 ends at 19:15 (Does NOT fit)")
