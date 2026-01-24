
import os
import sys
import django
import json

def setup_django(service_name):
    base_dir = f"/Users/PraveenWorks/Anil Works/Petleo-Backend/{service_name}"
    sys.path.append(base_dir)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"{service_name}.settings")
    django.setup()

def sync_all_permissions():
    # 1. SETUP SERVICE PROVIDER SERVICE
    os.environ["DJANGO_SETTINGS_MODULE"] = "service_provider_service.settings"
    sys.path.insert(0, "/Users/PraveenWorks/Anil Works/PetLeo-Backend/service_provider_service")
    import django
    django.setup()
    
    from service_provider.models import VerifiedUser, OrganizationEmployee
    
    # 2. COLLECT DATA
    all_users_data = []
    for u in VerifiedUser.objects.all():
        data = {
            "auth_user_id": u.auth_user_id,
            "email": u.email,
            "role": u.role,
            "permissions": u.permissions # Plan perms for Org
        }
        
        # If it's an employee, get their final perms (intersection)
        if u.role == "employee":
            try:
                emp = OrganizationEmployee.objects.get(auth_user_id=u.auth_user_id)
                data["permissions"] = emp.get_final_permissions()
            except:
                pass
        
        all_users_data.append(data)
        
    print(f"✅ Collected data for {len(all_users_data)} users from Service Provider Service.")

    # 3. SETUP VETERINARY SERVICE
    # Reset django setup for the next service
    from importlib import reload
    import django
    os.environ["DJANGO_SETTINGS_MODULE"] = "veterinary_service.settings"
    sys.path.insert(0, "/Users/PraveenWorks/Anil Works/Petleo-Backend/veterinary_service")
    # Reload settings/apps
    import veterinary_service.settings
    reload(veterinary_service.settings)
    django.setup()
    
    from veterinary.models import Clinic, VeterinaryStaff, StaffClinicAssignment
    
    # 4. PUSH DATA
    for user_data in all_users_data:
        uid = user_data["auth_user_id"]
        perms = user_data["permissions"]
        role = (user_data["role"] or "").lower()
        
        if role in ["organization", "individual"]:
            # Update all clinics for this org
            count = Clinic.objects.filter(organization_id=uid).update(capabilities={"permissions": perms})
            if count > 0:
                print(f"✅ Updated {count} Clinics for Org {user_data['email']} with {len(perms)} perms.")
        
        elif role != "customer":
            # Update Staff and Assignments
            staff, created = VeterinaryStaff.objects.update_or_create(
                auth_user_id=uid,
                defaults={"permissions": perms, "role": role}
            )
            a_count = StaffClinicAssignment.objects.filter(staff=staff).update(permissions=perms)
            print(f"✅ Updated Staff {user_data['email']} and {a_count} assignments with {len(perms)} perms.")

if __name__ == "__main__":
    # We can't easily switch django settings in one process due to app registry issues
    # So we'll do it via two separate scripts or just hardcode the ones we know.
    pass
