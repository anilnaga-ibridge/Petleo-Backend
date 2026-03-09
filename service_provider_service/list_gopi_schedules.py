from service_provider.models import OrganizationEmployee, ServiceProvider
from service_provider.models_scheduling import EmployeeDailySchedule
from datetime import date

gopi = ServiceProvider.objects.get(verified_user__full_name='Gopi g')
schedules = EmployeeDailySchedule.objects.filter(employee__organization=gopi)

print(f"Total Daily Schedules for Gopi's Org: {schedules.count()}")
for d in schedules:
    print(f" - Date: {d.date} | Employee: {d.employee.full_name} | Status: {d.status} | Time: {d.start_time}-{d.end_time}")

# Also check for Rahul explicitly again
r = OrganizationEmployee.objects.filter(full_name='Rahul', organization=gopi).first()
if r:
    print(f"\nRahul ID: {r.id}")
    r_schedules = EmployeeDailySchedule.objects.filter(employee=r)
    print(f"Rahul Daily Schedules: {r_schedules.count()}")
    for d in r_schedules:
        print(f" - Date: {d.date} | Status: {d.status}")
