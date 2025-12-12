import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

def drop_tables():
    with connection.cursor() as cursor:
        tables = [
            "provider_cart_providercartitem",
            "provider_cart_providercart",
            "provider_cart_purchasedplan"
        ]
        for table in tables:
            try:
                print(f"Dropping table {table}...")
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                print(f"Table {table} dropped.")
            except Exception as e:
                print(f"Error dropping table {table}: {e}")

if __name__ == "__main__":
    drop_tables()
