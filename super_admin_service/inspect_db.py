import os
import django
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'dynamic_fields_providerdocumentverification';
    """)
    columns = [row[0] for row in cursor.fetchall()]

print("COLUMNS IN dynamic_fields_providerdocumentverification:")
for col in columns:
    print(f"- {col}")

if 'definition_id' in columns:
    print("\n✅ definition_id EXISTS in database.")
else:
    print("\n❌ definition_id MISSING from database.")
