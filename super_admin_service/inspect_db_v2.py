import os
import django
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

with connection.cursor() as cursor:
    cursor.execute("SELECT current_database(), current_user, inet_server_addr(), inet_server_port();")
    db_info = cursor.fetchone()
    print(f"DATABASE INFO: {db_info}")

    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'dynamic_fields_providerdocumentverification'
        ORDER BY ordinal_position;
    """)
    columns = cursor.fetchall()

print("\nCOLUMNS IN dynamic_fields_providerdocumentverification:")
found = False
for col, dtype in columns:
    print(f"- {col} ({dtype})")
    if col == 'definition_id':
        found = True

if found:
    print("\n✅ definition_id EXISTS in database.")
else:
    print("\n❌ definition_id MISSING from database.")
