import os
import django
import requests
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from bookings.models import Booking

def fix_snapshots():
    # Find bookings with no snapshot or the default snapshot
    # Note: We can't easily filter by JSON field content in all DBs efficiently, 
    # so we'll iterate and check.
    
    print("Searching for bookings with missing or default snapshots...")
    
    bookings = Booking.objects.all().order_by('-created_at')[:50] # Check last 50 bookings
    
    updated_count = 0
    
    for booking in bookings:
        needs_update = False
        
        # Check if snapshot is missing
        if not booking.service_snapshot:
            needs_update = True
        
        # Check if snapshot is the specific default (fallback)
        elif booking.service_snapshot.get('service_name') == 'Veterinary Consultation' and \
             booking.service_snapshot.get('facility_name') == 'Service':
             # This is our fallback, let's see if we can get better data
             needs_update = True
        
        # Check if price is missing
        elif 'price' not in booking.service_snapshot:
            needs_update = True
             
        if needs_update:
            print(f"Checking Booking {booking.id} (Service: {booking.service_id}, Facility: {booking.facility_id})...")
            
            try:
                # Call the provider service resolution endpoint
                url = "http://localhost:8002/api/provider/resolve-details/"
                params = {
                    "service_id": booking.service_id,
                    "facility_id": booking.facility_id
                }
                
                response = requests.get(url, params=params, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  Found details: {data}")
                    
                    booking.service_snapshot = data
                    booking.save()
                    updated_count += 1
                    print("  Updated!")
                else:
                    print(f"  Failed to resolve: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"  Error calling provider service: {e}")

    print(f"\nDone. Updated {updated_count} bookings.")

if __name__ == "__main__":
    fix_snapshots()
