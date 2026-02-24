
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import PetOwner, Visit, Pet

print("--- PetOwners in Veterinary Service ---")
owners = PetOwner.objects.all()
for o in owners:
    print(f"ID: {o.id}, Name: {o.name}, Phone: {o.phone}, AuthUID: {o.auth_user_id}")

print("\n--- Visits in Veterinary Service ---")
visits = Visit.objects.all()
for v in visits:
    print(f"ID: {v.id}, Pet: {v.pet.name}, Status: {v.status}, OwnerUID: {v.pet.owner.auth_user_id}")
