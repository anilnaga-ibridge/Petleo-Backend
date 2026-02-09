import sys
import os
import django

print("PYTHON EXECUTABLE:", sys.executable)
print("PYTHON PATH:")
for p in sys.path:
    print(f"  - {p}")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from django.conf import settings
print("\nDATABASE SETTINGS:")
print(settings.DATABASES['default'])

from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT current_database(), current_user, inet_server_addr(), inet_server_port();")
    print("\nACTUAL DB CONNECTION:", cursor.fetchone())
