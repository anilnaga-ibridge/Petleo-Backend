from service_provider.models import OrganizationEmployee
from service_provider.models_scheduling import EmployeeDailySchedule, EmployeeWeeklySchedule
from datetime import date

target_date = date(2026, 2, 25)
rahuls = OrganizationEmployee.objects.filter(full_name__icontains='Rahul')
print(f"Total Rahuls found: {rahuls.count()}")

for r in rahuls:
    print(f"\nEmployee: {r.full_name} ({r.auth_user_id})")
    print(f"Organization: {r.organization.verified_user.full_name}")
    
    daily = EmployeeDailySchedule.objects.filter(employee=r, date=target_date)
    print(f"Daily Schedules ({target_date}):")
    for d in daily:
        print(f"  - Status: {d.status}, {d.start_time} to {d.end_time}, Off: {d.off}")
        
    weekly = EmployeeWeeklySchedule.objects.filter(employee=r, day_of_week=target_date.weekday())
    print(f"Weekly Schedules (Day {target_date.weekday()}):")
    for w in weekly:
        print(f"  - Status: {w.status}, {w.start_time} to {w.end_time}")
