
import os
import django
import sys

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/veterinary_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import FormDefinition, Pet, Clinic
from django.contrib.auth import get_user_model
User = get_user_model()

print("--- FormDefinitions ---")
forms = FormDefinition.objects.all()
for f in forms:
    print(f"ID: {f.id}, Code: {f.code}, Clinic: {f.clinic_id}")

if not forms.filter(code='VITALS').exists():
    print("\nWARNING: VITALS form definition missing!")

print("\n--- Clinics ---")
for c in Clinic.objects.all():
    print(f"Clinic: {c.id}, Name: {c.name}")

print("\n--- Users (first 5) ---")
for u in User.objects.all()[:5]:
    role = getattr(u, 'role', 'N/A')
    print(f"User: {u.username}, Role: {role}")
