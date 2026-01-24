
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import LabTestTemplate, LabTestField

def seed_labs():
    print("Seeding Lab Data...")
    
    # 1. Complete Blood Count (CBC)
    cbc, created = LabTestTemplate.objects.get_or_create(
        name="Complete Blood Count (CBC)",
        defaults={"description": "Standard blood panel related to red/white blood cells."}
    )
    
    if created:
        print("Created CBC Template")
        fields = [
            {"name": "Hemoglobin", "unit": "g/dL", "min": 12.0, "max": 17.5, "order": 1},
            {"name": "RBC Count", "unit": "millions/mcL", "min": 4.5, "max": 5.9, "order": 2},
            {"name": "WBC Count", "unit": "cells/mcL", "min": 4500, "max": 11000, "order": 3},
            {"name": "Platelets", "unit": "cells/mcL", "min": 150000, "max": 450000, "order": 4},
        ]
        for f in fields:
            LabTestField.objects.create(
                template=cbc,
                field_name=f["name"],
                unit=f["unit"],
                min_value=f["min"],
                max_value=f["max"],
                order=f["order"]
            )
    else:
        print("CBC Template already exists")

    # 2. Liver Function Test (LFT)
    lft, created = LabTestTemplate.objects.get_or_create(
        name="Liver Function Test (LFT)",
        defaults={"description": "Liver enzymes and bilirubin."}
    )

    if created:
        print("Created LFT Template")
        fields = [
            {"name": "Albumin", "unit": "g/dL", "min": 3.4, "max": 5.4, "order": 1},
            {"name": "Bilirubin", "unit": "mg/dL", "min": 0.1, "max": 1.2, "order": 2},
            {"name": "SGPT (ALT)", "unit": "U/L", "min": 7, "max": 56, "order": 3},
        ]
        for f in fields:
             LabTestField.objects.create(
                template=lft,
                field_name=f["name"],
                unit=f["unit"],
                min_value=f["min"],
                max_value=f["max"],
                order=f["order"]
            )
    else:
        print("LFT Template already exists")

if __name__ == "__main__":
    seed_labs()
