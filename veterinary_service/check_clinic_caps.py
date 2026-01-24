import os
import sys
import django
import json

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import Clinic

def check():
    # Organization ID for nagaanil29@gmail.com
    # I should find it first
    clinics = Clinic.objects.all()
    for c in clinics:
        print(f"Clinic: {c.name}")
        print(f"Org ID: {c.organization_id}")
        print(f"Capabilities: {json.dumps(c.capabilities, indent=2)}")
        print("-" * 20)

if __name__ == "__main__":
    check()
