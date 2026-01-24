import os
import django
import sys

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser
from org_employees.models import OrganizationEmployee as OE_v2
from service_provider.models import OrganizationEmployee as OE_v1

def check():
    print(f"VerifiedUser Count: {VerifiedUser.objects.count()}")
    print(f"org_employees.OrganizationEmployee Count: {OE_v2.objects.count()}")
    try:
        print(f"service_provider.OrganizationEmployee Count: {OE_v1.objects.count()}")
    except Exception as e:
        print(f"service_provider.OrganizationEmployee Error: {e}")
    
    users = VerifiedUser.objects.all()[:5]
    for u in users:
        print(f"User: {u.auth_user_id} - {u.role}")

    # Check if any user acts as an employee
    for u in users:
        if u.role and u.role not in ['customer', 'organization', 'individual']:
             print(f"Possible Employee found in VerifiedUser: {u.full_name} ({u.role})")

if __name__ == "__main__":
    check()
