import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee
from service_provider.models_scheduling import EmployeeDailySchedule, EmployeeWeeklySchedule

# Find Rahul
rahul = OrganizationEmployee.objects.filter(full_name__icontains='Rahul').first()
if not rahul:
    print("Employee Rahul not found.")
    sys.exit(1)

print(f"Employee: {rahul.full_name} (ID: {rahul.id} / Auth: {rahul.auth_user_id})")

# Check Daily Schedules for 2026-02-26
print("\n--- Daily Schedules for 2026-02-26 ---")
ds = EmployeeDailySchedule.objects.filter(employee=rahul, date='2026-02-26')
for s in ds:
    print(f"ID: {s.id} | Date: {s.date} | {s.start_time} - {s.end_time} | Status: {s.status} | Reason: {s.reason}")

# Check Weekly Schedules
print("\n--- Weekly Schedules ---")
ws = EmployeeWeeklySchedule.objects.filter(employee=rahul)
for s in ws:
    print(f"ID: {s.id} | Day: {s.get_day_of_week_display()} | {s.start_time} - {s.end_time} | Status: {s.status}")

# Check all daily schedules (to see if there are duplicates elsewhere)
print("\n--- All Daily Schedules (Last 5) ---")
all_ds = EmployeeDailySchedule.objects.filter(employee=rahul).order_by('-created_at')[:5]
for s in all_ds:
    print(f"Created: {s.created_at} | Date: {s.date} | {s.start_time} - {s.end_time} | Status: {s.status}")
