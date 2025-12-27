import os
import django
import sys
from django.db.models import Count

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee

def check_duplicates():
    print("--- Checking for Duplicates ---")
    
    # 1. Check VerifiedUser duplicates
    print("\nChecking VerifiedUser duplicates...")
    dupes = VerifiedUser.objects.values('auth_user_id').annotate(count=Count('id')).filter(count__gt=1)
    if dupes.exists():
        print(f"❌ Found {dupes.count()} duplicate VerifiedUsers!")
        for d in dupes:
            print(f" - Auth ID: {d['auth_user_id']} (Count: {d['count']})")
            users = VerifiedUser.objects.filter(auth_user_id=d['auth_user_id'])
            for u in users:
                print(f"   - ID: {u.id}, Email: {u.email}, Created: {u.created_at}")
    else:
        print("✅ No VerifiedUser duplicates found.")

    # 2. Check OrganizationEmployee duplicates
    print("\nChecking OrganizationEmployee duplicates...")
    dupes_emp = OrganizationEmployee.objects.values('auth_user_id').annotate(count=Count('id')).filter(count__gt=1)
    if dupes_emp.exists():
        print(f"❌ Found {dupes_emp.count()} duplicate OrganizationEmployees!")
        for d in dupes_emp:
            print(f" - Auth ID: {d['auth_user_id']} (Count: {d['count']})")
            emps = OrganizationEmployee.objects.filter(auth_user_id=d['auth_user_id'])
            for e in emps:
                print(f"   - ID: {e.id}, Email: {e.email}, Status: {e.status}")
    else:
        print("✅ No OrganizationEmployee duplicates found.")

if __name__ == "__main__":
    check_duplicates()
