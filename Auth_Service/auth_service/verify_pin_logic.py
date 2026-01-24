import os
import django
from datetime import datetime, timedelta


# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_service.settings')
django.setup()

from django.utils import timezone
from django.conf import settings

def test_expiry_calculation():
    print(f"Current Timezone: {timezone.get_current_timezone_name()}")
    
    # Mock times to test
    # 1. Early morning
    # 2. Noon
    # 3. Late night
    
    test_times = [
        datetime(2026, 1, 20, 0, 1, 0),    # 12:01 AM today
        datetime(2026, 1, 20, 12, 0, 0),   # 12:00 PM today
        datetime(2026, 1, 20, 23, 59, 0),  # 11:59 PM today
    ]
    
    tz = timezone.get_current_timezone()
    
    print("\n--- Testing Expiry Calculation Logic ---")
    
    for mock_now_naive in test_times:
        mock_now = timezone.make_aware(mock_now_naive, tz)
        
        # LOGIC FROM VIEWS.PY
        # tomorrow = now.date() + timedelta(days=1)
        # midnight = timezone.make_aware(datetime.combine(tomorrow, datetime.min.time()))
        
        tomorrow = mock_now.date() + timedelta(days=1)
        midnight_naive = datetime.combine(tomorrow, datetime.min.time())
        midnight = timezone.make_aware(midnight_naive, tz)
        
        duration = midnight - mock_now
        
        print(f"\nPin Set At:     {mock_now.strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
        print(f"Expires At:     {midnight.strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
        print(f"Valid Duration: {duration}")
        
        # ASSERTION
        # The expiry should ALWAYS be Jan 21st 00:00:00 for all Jan 20th times
        expected_expiry_naive = datetime(2026, 1, 21, 0, 0, 0)
        expected_expiry = timezone.make_aware(expected_expiry_naive, tz)
        
        if midnight == expected_expiry:
             print("✅ PASS: Expired at next Midnight")
        else:
             print("❌ FAIL: Did not expire at next Midnight")

if __name__ == "__main__":
    test_expiry_calculation()
