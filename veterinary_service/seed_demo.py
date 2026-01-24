import os
import django
import uuid
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import (
    Clinic, PetOwner, Pet, Visit, FormDefinition, FormField, FieldValidation
)
from django.contrib.auth import get_user_model

def seed_demo_data():
    print("🌱 Seeding Demo Data...")

    # 1. Ensure Clinic Exists (Mocking Provider Service sync)
    clinic, created = Clinic.objects.get_or_create(
        organization_id="demo-provider-id",
        defaults={
            "name": "PetLeo Demo Clinic",
            "capabilities": {"VETERINARY_MODULE": True}
        }
    )
    if created:
        print(f"✅ Created Clinic: {clinic.name}")
    else:
        print(f"ℹ️ Clinic already exists: {clinic.name}")

    # 2. Create Form Definitions
    forms = [
        {
            "code": "VITALS",
            "name": "Vitals Check",
            "fields": [
                {"field_key": "weight", "label": "Weight", "field_type": "NUMBER", "unit": "kg", "is_required": True, "order": 1, "validations": [{"min_value": 0.1, "max_value": 100}]},
                {"field_key": "temperature", "label": "Temperature", "field_type": "NUMBER", "unit": "°C", "is_required": True, "order": 2, "validations": [{"min_value": 35, "max_value": 43}]},
                {"field_key": "heart_rate", "label": "Heart Rate", "field_type": "NUMBER", "unit": "bpm", "is_required": True, "order": 3},
                {"field_key": "respiratory_rate", "label": "Respiratory Rate", "field_type": "NUMBER", "unit": "bpm", "is_required": False, "order": 4},
                {"field_key": "mucous_membrane", "label": "Mucous Membrane", "field_type": "SELECT", "metadata": {"options": ["Pink", "Pale", "Cyanotic", "Icteric"]}, "is_required": True, "order": 5},
            ]
        },
        {
            "code": "PRESCRIPTION",
            "name": "Prescription",
            "fields": [
                # In a real dynamic form, this might be a repeatable group. 
                # For Phase 4 demo, we'll use a simplified structure or assume the frontend handles the repeatable part 
                # and submits a JSON structure that matches what the backend expects.
                # However, the prompt asked for "dynamic form renderer" to handle this.
                # To keep it simple for the demo, let's define fields for a SINGLE medicine entry 
                # and assume the doctor adds them one by one or the form allows multiple submissions.
                # BETTER APPROACH for Demo: A "Prescription Note" text area and a structured "Medicines" JSON field if possible.
                # But DynamicField is simple. Let's make it a simple text area for "Instructions" and "Medicines List" for now
                # OR define specific fields for one medicine.
                
                # Let's go with a JSON schema approach where the frontend might be smarter, 
                # BUT the prompt said "All doctor forms must use the SAME dynamic form renderer".
                # So we will define fields for ONE medicine.
                {"field_key": "medicine_name", "label": "Medicine Name", "field_type": "TEXT", "is_required": True, "order": 1},
                {"field_key": "dosage", "label": "Dosage", "field_type": "TEXT", "is_required": True, "order": 2, "metadata": {"placeholder": "e.g. 500mg"}},
                {"field_key": "frequency", "label": "Frequency", "field_type": "SELECT", "metadata": {"options": ["1-0-0", "1-0-1", "1-1-1", "0-0-1", "SOS"]}, "is_required": True, "order": 3},
                {"field_key": "duration_days", "label": "Duration (Days)", "field_type": "NUMBER", "is_required": True, "order": 4},
                {"field_key": "instructions", "label": "Special Instructions", "field_type": "TEXTAREA", "is_required": False, "order": 5},
            ]
        },
        {
            "code": "LAB_ORDER",
            "name": "Lab Order",
            "fields": [
                {"field_key": "test_type", "label": "Test Type", "field_type": "SELECT", "metadata": {"options": ["CBC", "Biochemistry", "Urinalysis", "X-Ray", "Ultrasound"]}, "is_required": True, "order": 1},
                {"field_key": "priority", "label": "Priority", "field_type": "SELECT", "metadata": {"options": ["Routine", "Urgent", "Stat"]}, "is_required": True, "order": 2},
                {"field_key": "clinical_notes", "label": "Clinical Notes", "field_type": "TEXTAREA", "is_required": False, "order": 3},
            ]
        },
        {
            "code": "LAB_RESULTS",
            "name": "Lab Results",
            "fields": [
                {"field_key": "test_name", "label": "Test Name", "field_type": "TEXT", "is_required": True, "order": 1}, # Should ideally match order
                {"field_key": "result_value", "label": "Result", "field_type": "TEXTAREA", "is_required": True, "order": 2},
                {"field_key": "is_abnormal", "label": "Abnormal?", "field_type": "BOOLEAN", "is_required": False, "order": 3},
                {"field_key": "technician_notes", "label": "Technician Notes", "field_type": "TEXTAREA", "is_required": False, "order": 4},
            ]
        }
    ]

    for form_data in forms:
        fields_data = form_data.pop('fields')
        form, _ = FormDefinition.objects.update_or_create(
            code=form_data['code'],
            defaults={**form_data, "clinic": clinic}
        )
        print(f"✅ Form Definition: {form.name}")
        
        # Clear existing fields to avoid duplicates during re-seed
        FormField.objects.filter(form_definition=form).delete()
        
        for field_data in fields_data:
            validations = field_data.pop('validations', [])
            field = FormField.objects.create(form_definition=form, **field_data)
            for val in validations:
                FieldValidation.objects.create(form_field=field, **val)
            print(f"   - Field: {field.label}")

    # 3. Create Demo Owner & Pet
    owner, _ = PetOwner.objects.get_or_create(
        clinic=clinic,
        phone="9876543210",
        defaults={
            "email": "ravi.kumar@example.com",
            "name": "Ravi Kumar",
            "address": "456 Park Avenue"
        }
    )
    print(f"✅ Owner: {owner.name}")

    pet, _ = Pet.objects.get_or_create(
        owner=owner,
        name="Tommy",
        defaults={
            "species": "Dog",
            "breed": "Labrador"
        }
    )
    print(f"✅ Pet: {pet.name}")

    print("\n🎉 Demo Data Seeded Successfully!")

if __name__ == "__main__":
    seed_demo_data()
