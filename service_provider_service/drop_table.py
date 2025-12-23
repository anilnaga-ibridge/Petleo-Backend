import os
import django
import sys
from django.db import connection

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

with connection.cursor() as cursor:
    tables = [
        "provider_dynamic_fields_localdocumentdefinition",
        "provider_dynamic_fields_localfielddefinition",
        "provider_dynamic_fields_providertemplatecategory",
        "provider_dynamic_fields_providertemplateservice",
        "provider_dynamic_fields_providercategory",
        "provider_dynamic_fields_providerdocument",
        "provider_dynamic_fields_providerfacility",
        "provider_dynamic_fields_providerpricing",
        "provider_dynamic_fields_providertemplatefacility",
        "provider_dynamic_fields_providertemplatepricing",
        "provider_dynamic_fields_providerfieldvalue",
        "provider_dynamic_fields_providercapabilityaccess"
    ]
    for table in tables:
        print(f"Dropping table {table}...")
        cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
    print("All tables dropped.")
