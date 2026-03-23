import os
import django
import uuid
from datetime import date, datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import Pet, Medicine, MedicineReminder, MedicineReminderSchedule, PetOwner, Clinic

def test_reminder_generation():
    print("Testing Medicine Reminder Generation...")
    
    # Get or create dummy data
    clinic = Clinic.objects.first()
    owner = PetOwner.objects.filter(clinic=clinic).first()
    pet = Pet.objects.filter(owner=owner).first()
    medicine = Medicine.objects.filter(clinic=clinic).first()
    
    if not medicine:
        medicine = Medicine.objects.create(
            clinic=clinic,
            name="Test Medicine",
            manufacturer="Test Labs"
        )

    # Create a 3-day reminder, twice a day
    reminder = MedicineReminder.objects.create(
        pet=pet,
        pet_owner_auth_id=str(owner.auth_user_id),
        medicine=medicine,
        dosage="1 tab",
        food_instruction="AFTER_FOOD",
        reminder_times=["09:00", "21:00"],
        start_date=date.today(),
        end_date=date.today().replace(day=date.today().day + 2) if date.today().day < 28 else date.today(),
        is_active=True
    )
    
    schedules = MedicineReminderSchedule.objects.filter(reminder=reminder)
    print(f"Generated {schedules.count()} schedule entries.")
    for s in schedules:
        print(f" - {s.scheduled_datetime} | {s.status}")

    if schedules.count() == 6:
        print("✅ SUCCESS: 6 entries generated for 3 days x 2 times.")
    else:
        print(f"❌ FAILURE: Expected 6 entries, got {schedules.count()}.")

if __name__ == "__main__":
    test_reminder_generation()
