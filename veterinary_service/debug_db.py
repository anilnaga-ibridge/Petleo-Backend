
import os
import django
import sys
import json

# Add project root to path
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/veterinary_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.services import MetadataService

visit_id = '951dc56f-1595-4085-a367-ebef71df1f82'
try:
    summary = MetadataService.get_visit_summary(visit_id)
    print("--- Service Response ---")
    # Serialize to JSON to Ensure it's valid JSON
    print(json.dumps(summary, indent=4, default=str)) 
except Exception as e:
    print(f"Error: {e}")
