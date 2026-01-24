import os
import django
import json
import sys

# Setup Django Environment
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/veterinary_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import Visit, FormSubmission
from veterinary.services import MetadataService

def verify_visit(visit_id):
    print(f"--- Verifying Visit: {visit_id} ---")
    try:
        visit = Visit.objects.get(id=visit_id)
        print(f"Visit Found: {visit.id} | Status: {visit.status} | Pet: {visit.pet.name if visit.pet else 'None'}")
        
        # Check Submissions
        submissions = FormSubmission.objects.filter(visit=visit)
        print(f"Total Submissions: {submissions.count()}")
        
        for sub in submissions:
            print(f" - Submission ID: {sub.id} | Form: {sub.form_definition.code}")
            if sub.form_definition.code == 'PRESCRIPTION':
                 print(f"   PRESCRIPTION DATA: {json.dumps(sub.data, indent=2)}")

        # Check Summary
        summary = MetadataService.get_visit_summary(visit.id)
        if 'forms' in summary and 'PRESCRIPTION' in summary['forms']:
             print(f"Summary Service: FOUND {len(summary['forms']['PRESCRIPTION'])} Prescription Forms")
             print(json.dumps(summary['forms']['PRESCRIPTION'], indent=2, default=str)) # default=str for datetime
        else:
             print("Summary Service: NO Prescription Forms found in summary['forms']")
             
        # Check direct prescription relation
        if hasattr(visit, 'prescription_details'):
             print("Visit has related 'prescription_details' (checking if mapped via property...)")
             # Assuming 'prescription' in summary comes from a real model or aggregated data
             
        if 'prescription' in summary:
             print(f"Summary Service 'prescription' key: {json.dumps(summary['prescription'], indent=2, default=str)}")
        else:
             print("Summary Service: 'prescription' key MISSING")

    except Visit.DoesNotExist:
        print("Visit not found!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    visit_id = '9055f4c4-ed42-49a5-9b6a-eee0fae759b9'
    verify_visit(visit_id)
