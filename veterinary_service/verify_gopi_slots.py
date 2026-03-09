"""
Verification Script: Test that VeterinaryAvailabilityService now returns slots for Gopi g.

Run from veterinary_service directory:
    python3 verify_gopi_slots.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.services import VeterinaryAvailabilityService

# Gopi g's clinic in veterinary_service
GOPI_CLINIC_ID = '8661f33e-26b0-484c-af2b-7a3cf4334c48'
GOPI_AUTH_ID   = '87b9cb5d-ee9e-4e20-bf22-646b30b793ed'

# Use a dummy service_id — the availability service doesn't filter on facility inside vet_service
# It just passes it as a query param to service_provider_service
SERVICE_ID = 'consultation'

def verify():
    for date_str in ['2026-02-24', '2026-02-25']:
        print(f"\n📅 Testing {date_str} (doctor={GOPI_AUTH_ID})...")
        slots = VeterinaryAvailabilityService.get_doctor_available_slots(
            clinic_id=GOPI_CLINIC_ID,
            service_id=SERVICE_ID,
            target_date=date_str,
            doctor_auth_id=GOPI_AUTH_ID,
        )
        if slots:
            print(f"✅ {len(slots)} slot(s) found: {slots[:5]}{'...' if len(slots) > 5 else ''}")
        else:
            print("❌ No slots returned — check service_provider_service availability API is reachable.")

if __name__ == "__main__":
    verify()
