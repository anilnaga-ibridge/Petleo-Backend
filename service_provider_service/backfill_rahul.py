import os
import django
import sys
from datetime import date, time

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ServiceProvider
from service_provider.models_scheduling import EmployeeDailySchedule

def backfill_rahul_schedule():
    # 1. Find Rahul
    rahul = OrganizationEmployee.objects.filter(full_name='Rahul').first()
    if not rahul:
        print("Rahul not found")
        return

    # 2. Create APPROVED schedule for today
    target_date = date(2026, 2, 25)
    
    # Check if exists (shouldn't, based on previous checks)
    sched, created = EmployeeDailySchedule.objects.get_or_create(
        employee=rahul,
        date=target_date,
        defaults={
            'start_time': time(9, 0),
            'end_time': time(19, 0),
            'status': 'APPROVED',
            'reason': 'Manual Backfill to restore missing slots'
        }
    )
    
    if created:
        print(f"Successfully created APPROVED schedule for Rahul on {target_date}")
    else:
        print(f"Schedule already existed for Rahul on {target_date}. Status: {sched.status}")
        if sched.status != 'APPROVED':
            sched.status = 'APPROVED'
            sched.save()
            print(f"Updated status to APPROVED")

if __name__ == "__main__":
    backfill_rahul_schedule()
