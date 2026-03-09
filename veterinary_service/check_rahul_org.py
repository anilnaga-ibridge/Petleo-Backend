import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import StaffClinicAssignment, VeterinaryStaff
import sys

rahul_auth_id = '5c3b54b9-aa99-441d-8598-df3aea0b59fd'

print("--- Veterinary Service ---")
assignments = StaffClinicAssignment.objects.filter(staff__auth_user_id=rahul_auth_id)
print(f"Total Assignments for {rahul_auth_id}: {assignments.count()}")
for a in assignments:
    print(f"Assignment ID: {a.id}")
    print(f"Clinic Name: {a.clinic.name}")
    print(f"Clinic Org ID: {a.clinic.organization_id}")
    print(f"Role: {a.role}")

print("\n--- Service Provider Service ---")
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ["DJANGO_SETTINGS_MODULE"] = "service_provider_service.settings"
# Note: Changing DJANGO_SETTINGS_MODULE dynamically after setup isn't always reliable, 
# but let's just do a second script or run it directly for service_provider
