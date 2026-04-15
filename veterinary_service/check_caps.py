
import os
import django
import sys

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/veterinary_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import Clinic

print("--- Clinic Capabilities ---")
for c in Clinic.objects.all():
    print(f"Clinic: {c.name}, Capabilities: {c.capabilities}")
