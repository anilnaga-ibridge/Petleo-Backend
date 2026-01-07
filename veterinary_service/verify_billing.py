import os
import django
import uuid

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import Clinic, PetOwner, Pet, Visit, VisitInvoice, VisitCharge

def test_billing_flow():
    print("--- Testing Billing Flow ---")
    
    # 1. Setup Clinic, Owner, Pet
    clinic, _ = Clinic.objects.get_or_create(
        provider_id=str(uuid.uuid4()),
        defaults={"name": "Test Clinic"}
    )
    
    owner, _ = PetOwner.objects.get_or_create(
        clinic=clinic,
        phone="1234567890",
        defaults={"name": "John Doe", "auth_user_id": str(uuid.uuid4())}
    )
    
    pet, _ = Pet.objects.get_or_create(
        owner=owner,
        name="Buddy",
        defaults={"species": "Dog"}
    )
    
    # 2. Create Visit (should trigger invoice and consultation charge)
    print("Creating Visit...")
    visit = Visit.objects.create(
        clinic=clinic,
        pet=pet,
        status='CREATED'
    )
    
    invoice = VisitInvoice.objects.get(visit=visit)
    print(f"Invoice created: {invoice.id}")
    print(f"Charges: {list(invoice.charges.values_list('charge_type', 'amount'))}")
    print(f"Total: {invoice.total}")
    
    # 3. Transition to LAB_ORDERED (should trigger lab charge)
    print("Transitioning to LAB_ORDERED...")
    visit.status = 'LAB_ORDERED'
    visit.save()
    
    invoice.refresh_from_db()
    print(f"Charges after Lab: {list(invoice.charges.values_list('charge_type', 'amount'))}")
    print(f"Total: {invoice.total}")
    
    # 4. Pay Invoice
    print("Paying Invoice...")
    invoice.status = 'PAID'
    invoice.save()
    print(f"Invoice Status: {invoice.status}")

if __name__ == "__main__":
    test_billing_flow()
