"""
Fix Script: Create an approved daily schedule for the 2026-02-24 date for Gopi g.

Since AvailabilityService checks EmployeeDailySchedule > EmployeeWeeklySchedule,
we need to create an APPROVED EmployeeDailySchedule for Gopi on 2026-02-24.

Run this script from the service_provider_service directory:
    python3 fix_gopi_schedule.py
"""
import os
import django
from datetime import time, date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee
from service_provider.models_scheduling import EmployeeDailySchedule

# Gopi g's known identifiers
GOPI_AUTH_USER_ID = '87b9cb5d-ee9e-4e20-bf22-646b30b793ed'

# Dates to add schedules for (today and tomorrow)
TARGET_DATES = [date(2026, 2, 24), date(2026, 2, 25)]
START_TIME = time(9, 0)   # 09:00
END_TIME   = time(17, 0)  # 17:00

def fix_gopi_schedule():
    print("🔍 Looking up Gopi's OrganizationEmployee...")
    try:
        emp = OrganizationEmployee.objects.get(auth_user_id=GOPI_AUTH_USER_ID)
        print(f"✅ Found: {emp.full_name} (status={emp.status})")
    except OrganizationEmployee.DoesNotExist:
        print("❌ OrganizationEmployee not found for Gopi!")
        print("   Please run fix_gopi_employee_record.py first.")
        return

    for target_date in TARGET_DATES:
        print(f"\n📅 Processing date: {target_date}")
        existing = EmployeeDailySchedule.objects.filter(
            employee=emp,
            date=target_date
        ).first()

        if existing:
            print(f"ℹ️  Schedule found: {existing.start_time}-{existing.end_time} | status={existing.status}")
            if existing.status != 'APPROVED':
                existing.status = 'APPROVED'
                existing.save()
                print(f"✅ Approved the existing schedule for {target_date}.")
        else:
            sched = EmployeeDailySchedule.objects.create(
                employee=emp,
                date=target_date,
                start_time=START_TIME,
                end_time=END_TIME,
                reason='Regular Work Day',
                status='APPROVED',
            )
            print(f"✅ Created APPROVED schedule: {sched.start_time}-{sched.end_time} on {target_date}")

    print("\n✅ All schedules processed. Gopi g should now have available slots.")
    print("   Refresh the booking page and select date 2026-02-24 or 2026-02-25.")

if __name__ == "__main__":
    fix_gopi_schedule()
