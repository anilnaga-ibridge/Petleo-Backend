import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import StaffClinicAssignment
assignments = StaffClinicAssignment.objects.all()
fixed = 0
for a in assignments:
    if a.permissions and isinstance(a.permissions, list) and len(a.permissions) > 0 and isinstance(a.permissions[0], dict):
        # Flatten
        flat = []
        for p in a.permissions:
            if 'capability_key' in p:
                flat.append(p['capability_key'])
        
        a.permissions = list(set(flat))
        a.save()
        fixed += 1
        print(f"Fixed assignment {a.id} for {a.staff.full_name} ({a.role}) -> {a.permissions}")

print(f"Fixed {fixed} assignments in veterinary_service.")
