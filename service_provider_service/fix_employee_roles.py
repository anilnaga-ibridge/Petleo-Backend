
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import OrganizationEmployee, VerifiedUser

fixes = {
    "doctor@gmail.com": "doctor",
    "receptionist2@gmail.com": "receptionist",
    "receptionist@gmail.com": "receptionist",
    "eswar@gmail.com": "employee"
}

for email, role in fixes.items():
    # Update VerifiedUser
    try:
        user = VerifiedUser.objects.get(email=email)
        user.role = role
        user.save()
        print(f"✅ Updated VerifiedUser {email} to {role}")
    except VerifiedUser.DoesNotExist:
        print(f"⚠️ VerifiedUser {email} not found")

    # Update OrganizationEmployee
    try:
        emp = OrganizationEmployee.objects.get(email=email)
        emp.role = role
        emp.save()
        print(f"✅ Updated OrganizationEmployee {email} to {role}")
    except OrganizationEmployee.DoesNotExist:
        print(f"⚠️ OrganizationEmployee {email} not found")

print("Done.")
