import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee
from service_provider.models_scheduling import EmployeeDailySchedule, EmployeeWeeklySchedule

def check_schedules():
    # Gopi's org provider ID: 9c856d87-e98f-42fd-a474-dc71fc547537
    emp_list = OrganizationEmployee.objects.filter(organization_id='9c856d87-e98f-42fd-a474-dc71fc547537')
    
    print(f"Employees in Gopi's org: {emp_list.count()}")
    for emp in emp_list:
        print(f"\n  Employee: {emp.full_name} | auth_user_id: {emp.auth_user_id}")
        
        daily = EmployeeDailySchedule.objects.filter(employee=emp).order_by('-date')[:5]
        print(f"  Daily Schedules (last 5):")
        for d in daily:
            print(f"    date={d.date} | {d.start_time}-{d.end_time} | status={d.status}")
        
        weekly = EmployeeWeeklySchedule.objects.filter(employee=emp)[:7]
        print(f"  Weekly Schedules:")
        for w in weekly:
            days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
            print(f"    day={days[w.day_of_week] if w.day_of_week < 7 else w.day_of_week} | {w.start_time}-{w.end_time} | active={w.is_active}")

if __name__ == "__main__":
    check_schedules()
