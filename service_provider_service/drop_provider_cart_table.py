import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

def drop_table():
    with connection.cursor() as cursor:
        try:
            print("Dropping table provider_cart_providercart...")
            cursor.execute("DROP TABLE IF EXISTS provider_cart_providercart CASCADE;")
            print("Table dropped.")
        except Exception as e:
            print(f"Error dropping table: {e}")

if __name__ == "__main__":
    drop_table()
