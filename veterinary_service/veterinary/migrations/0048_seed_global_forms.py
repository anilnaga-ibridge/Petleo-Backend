
from django.db import migrations

def seed_global_forms(apps, schema_editor):
    FormDefinition = apps.get_model('veterinary', 'FormDefinition')
    FormField = apps.get_model('veterinary', 'FormField')
    
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
        # We use update_or_create to avoid duplicates if migration is re-run or partially failed
        form, created = FormDefinition.objects.update_or_create(
            code=form_data['code'],
            defaults={**form_data, "clinic": None} 
        )
        
        # Sync fields
        FormField.objects.filter(form_definition=form).delete()
        for field_data in fields_data:
            FormField.objects.create(form_definition=form, **field_data)

def remove_global_forms(apps, schema_editor):
    FormDefinition = apps.get_model('veterinary', 'FormDefinition')
    FormDefinition.objects.filter(code__in=["VITALS", "PRESCRIPTION", "LAB_ORDER"], clinic=None).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('veterinary', '0047_medicalappointment_meeting_link_and_more'), # Dependencies are important
    ]

    operations = [
        migrations.RunPython(seed_global_forms, remove_global_forms),
    ]
