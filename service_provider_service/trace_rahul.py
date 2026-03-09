import os
import django
import sys
from datetime import date

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ServiceProvider
from service_provider.models_scheduling import EmployeeDailySchedule, EmployeeWeeklySchedule

def find_rahul_and_schedules():
    print("--- Searching for Rahul ---")
    rahuls = OrganizationEmployee.objects.filter(full_name__icontains="Rahul")
    print(f"Found {rahuls.count()} employees with name containing 'Rahul'")
    
    for r in rahuls:
        print(f"\nEmployee: {r.full_name} | ID: {r.id} | AuthID: {r.auth_user_id} | Org: {r.organization.verified_user.full_name}")
        
        # Check daily schedules for 2026-02-25
        target_date = date(2026, 2, 25)
        daily = EmployeeDailySchedule.objects.filter(employee=r, date=target_date)
        print(f" - Daily Schedules for {target_date}: {daily.count()}")
        for d in daily:
            print(f"   * Status: {d.status} | {d.start_time} - {d.end_time} | Off: {d.off}")
            
        # Check weekly schedules
        weekday = target_date.weekday()
        weekly = EmployeeWeeklySchedule.objects.filter(employee=r, day_of_week=weekday)
        print(f" - Weekly Schedules for weekday {weekday}: {weekly.count()}")
        for w in weekly:
            print(f"   * Status: {w.status} | {w.start_time} - {w.end_time}")

if __name__ == "__main__":
    find_rahul_and_schedules()
