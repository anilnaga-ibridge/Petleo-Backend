import os
import django
import sys
from django.db import connection

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'provider_dynamic_fields_providercapabilityaccess';")
    columns = [col[0] for col in cursor.fetchall()]
    print("Columns in provider_dynamic_fields_providercapabilityaccess:")
    print(columns)
