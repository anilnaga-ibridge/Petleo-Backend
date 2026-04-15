
import os
import django
import sys
import uuid

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/veterinary_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import (
    Clinic, FormDefinition, FormField, FieldValidation
)

def fix_production_data():
    print("🚀 Running PRODUCTION-LEVEL Fix Script...")

    # 1. Enable VETERINARY_MODULE for all existing clinics
    clinics = Clinic.objects.all()
    print(f"🏥 Updating {clinics.count()} clinics...")
    for clinic in clinics:
        caps = clinic.capabilities or {}
        if not caps.get('VETERINARY_MODULE'):
            caps['VETERINARY_MODULE'] = True
            clinic.capabilities = caps
            clinic.save()
            print(f"   ✅ Enabled VETERINARY_MODULE for: {clinic.name}")
        else:
            print(f"   ℹ️ VETERINARY_MODULE already enabled for: {clinic.name}")

    # 2. Seed Global Form Definitions
    forms = [
        {
            "code": "VITALS",
            "name": "Vitals Check",
            "description": "Standard vitals check for veterinary visits",
            "fields": [
                {"field_key": "weight", "label": "Weight", "field_type": "NUMBER", "unit": "kg", "is_required": True, "order": 1},
                {"field_key": "temperature", "label": "Temperature", "field_type": "NUMBER", "unit": "°C", "is_required": True, "order": 2},
                {"field_key": "pulse", "label": "Pulse Rate", "field_type": "NUMBER", "unit": "bpm", "is_required": False, "order": 3},
                {"field_key": "respiration", "label": "Respiratory Rate", "field_type": "NUMBER", "unit": "bpm", "is_required": False, "order": 4},
                {"field_key": "mucous_membrane", "label": "Mucous Membrane", "field_type": "SELECT", "metadata": {"options": ["Pink", "Pale", "Cyanotic", "Icteric"]}, "is_required": False, "order": 5},
            ]
        },
        {
            "code": "PRESCRIPTION",
            "name": "Prescription",
            "description": "Veterinary prescription form",
            "fields": [
                {"field_key": "medicine_name", "label": "Medicine", "field_type": "TEXT", "is_required": True, "order": 1},
                {"field_key": "dosage", "label": "Dosage", "field_type": "TEXT", "is_required": True, "order": 2},
                {"field_key": "frequency", "label": "Frequency", "field_type": "TEXT", "is_required": True, "order": 3},
                {"field_key": "duration", "label": "Duration (Days)", "field_type": "NUMBER", "is_required": True, "order": 4},
                {"field_key": "instructions", "label": "Instructions", "field_type": "TEXTAREA", "is_required": False, "order": 5},
            ]
        },
        {
            "code": "LAB_ORDER",
            "name": "Lab Order",
            "description": "Laboratory test request",
            "fields": [
                {"field_key": "test_type", "label": "Test Type", "field_type": "TEXT", "is_required": True, "order": 1},
                {"field_key": "clinical_history", "label": "Clinical History", "field_type": "TEXTAREA", "is_required": False, "order": 2},
            ]
        }
    ]

    for form_data in forms:
        fields_data = form_data.pop('fields')
        form, created = FormDefinition.objects.update_or_create(
            code=form_data['code'],
            defaults={**form_data, "clinic": None} # Set clinic=None for GLOBAL visibility
        )
        print(f"{'✅ Created' if created else '🔄 Updated'} Global Form: {form.name}")
        
        # Clear/Update fields
        FormField.objects.filter(form_definition=form).delete()
        for field_data in fields_data:
            FormField.objects.create(form_definition=form, **field_data)

    print("\n✨ PRODUCTION-LEVEL Fix Applied Successfully!")

if __name__ == "__main__":
    fix_production_data()
