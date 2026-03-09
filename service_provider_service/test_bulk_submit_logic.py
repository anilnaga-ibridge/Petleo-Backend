import os
import django
import sys
from datetime import date
import json

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ServiceProvider
from service_provider.models_scheduling import EmployeeDailySchedule
from django.test import RequestFactory
from service_provider.views_availability import ScheduleViewSet
from django.contrib.auth.models import AnonymousUser

class MockUser:
    def __init__(self, auth_user_id):
        self.auth_user_id = auth_user_id
        self.is_authenticated = True

def test_bulk_submit():
    # 1. Setup Employee (Rahul)
    rahul = OrganizationEmployee.objects.filter(full_name='Rahul').first()
    if not rahul:
        print("Rahul not found")
        return

    # Mock request
    factory = RequestFactory()
    url = '/api/provider/schedules/bulk-submit/'
    data = {
        "schedule": [
            {
                "date": "2026-02-25",
                "start_time": "09:00:00",
                "end_time": "19:00:00",
                "reason": "Test 25",
                "off": False
            },
            {
                "date": "2026-02-26",
                "start_time": "08:00:00",
                "end_time": "18:00:00",
                "reason": "Test 26",
                "off": False
            }
        ]
    }
    
    request = factory.post(url, data=json.dumps(data), content_type='application/json')
    request.user = MockUser(rahul.auth_user_id)
    
    # 2. Call bulk_submit
    view = ScheduleViewSet.as_view({'post': 'bulk_submit'})
    response = view(request)
    
    print(f"Response Status: {response.status_code}")
    
    # 3. Verify results in DB
    schedules = EmployeeDailySchedule.objects.filter(employee=rahul, date__in=['2026-02-25', '2026-02-26']).order_by('date')
    print(f"\nSchedules in DB after test:")
    for s in schedules:
        print(f" - {s.date} | {s.status} | {s.start_time}-{s.end_time} | Reason: {s.reason}")

if __name__ == "__main__":
    test_bulk_submit()
