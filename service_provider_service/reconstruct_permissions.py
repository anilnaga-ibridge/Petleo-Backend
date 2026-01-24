import os
import sys
import django
import json

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee
from service_provider.utils import _build_permission_tree

def check():
    email = "nagaanil29@gmail.com"
    user = VerifiedUser.objects.get(email=email)
    
    # 3. Fetch Capabilities using the robust helper
    permissions_list = _build_permission_tree(user)

    # Mimic injection logic from views.py
    user_caps = user.get_all_plan_capabilities()
    user_caps.add("VETERINARY_CORE")
    
    simple_services = {
        "GROOMING": {"name": "Grooming", "icon": "tabler-cut"},
        "DAYCARE": {"name": "Daycare", "icon": "tabler-bone"},
        "TRAINING": {"name": "Training", "icon": "tabler-school"},
        "BOARDING": {"name": "Boarding", "icon": "tabler-home"},
        "VETERINARY_VISITS": {"name": "Visits", "icon": "tabler-calendar"},
        "VETERINARY_VITALS": {"name": "Vitals", "icon": "tabler-activity"},
        "VETERINARY_PRESCRIPTIONS": {"name": "Prescriptions", "icon": "tabler-pill"},
        "VETERINARY_LABS": {"name": "Lab Orders", "icon": "tabler-microscope"},
        "VETERINARY_MEDICINE_REMINDERS": {"name": "Medicine", "icon": "tabler-alarm"},
        "VETERINARY_DOCTOR": {"name": "Doctor Queue", "icon": "tabler-stethoscope"},
        "VETERINARY_PHARMACY": {"name": "Pharmacy", "icon": "tabler-band-aid"},
        "VETERINARY_CORE": {"name": "Veterinary", "icon": "tabler-stethoscope"}
    }

    for key, meta in simple_services.items():
        if key in user_caps:
            if not any(p.get('service_key') == key for p in permissions_list):
                permissions_list.append({
                    "service_id": key,
                    "service_name": meta["name"],
                    "service_key": key,
                    "icon": meta["icon"],
                    "categories": [],
                    "can_view": True,
                    "can_create": True,
                    "can_edit": True,
                    "can_delete": True
                })
    
    print(json.dumps(permissions_list, indent=2))

if __name__ == "__main__":
    check()
