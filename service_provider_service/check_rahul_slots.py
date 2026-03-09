import os
import django
import sys
from datetime import date

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ServiceProvider
from service_provider.models_scheduling import EmployeeDailySchedule
from service_provider.services.availability_service import AvailabilityService

def check_rahul_slots():
    # 1. Find Gopi's Org
    gopi_sp = ServiceProvider.objects.filter(verified_user__full_name="Gopi g").first()
    if not gopi_sp:
        print("Gopi g not found")
        return

    # 2. Find Rahul in Gopi's Org
    rahul = OrganizationEmployee.objects.filter(organization=gopi_sp, full_name="Rahul").first()
    if not rahul:
        print(f"Rahul not found in {gopi_sp}'s organization")
        # List all employees to be sure
        print("Employees in Org:")
        for emp in gopi_sp.employees.all():
            print(f" - {emp.full_name} ({emp.auth_user_id})")
        return

    print(f"Found Rahul: {rahul.auth_user_id}")
    
    # 3. Check Schedule for 2026-02-25
    target_date = date(2026, 2, 25)
    sched = EmployeeDailySchedule.objects.filter(employee=rahul, date=target_date).first()
    if sched:
        print(f"Schedule found: {sched.date} | {sched.start_time} - {sched.end_time} | Status: {sched.status} | Off: {sched.off}")
    else:
        print(f"No daily schedule found for {target_date}")

    # 4. Try generating slots
    # We need a facility_id if possible, but let's try without it first (defaults to 60 mins)
    slots = AvailabilityService.get_available_slots(rahul.auth_user_id, None, target_date)
    print(f"\nGenerated Slots (60 min duration): {slots}")

    # 5. Check if blocked
    from service_provider.services.availability_service import is_slot_booked_or_blocked
    if sched:
        print(f"Is 09:00 blocked? {is_slot_booked_or_blocked(rahul.auth_user_id, target_date, sched.start_time)}")

if __name__ == "__main__":
    check_rahul_slots()
