
import os
import django
import sys
from django.db import connection

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

def reset_app():
    with connection.cursor() as cursor:
        # 1. Clear migration history
        print("Clearing migration history for plans_coupens...")
        cursor.execute("DELETE FROM django_migrations WHERE app = 'plans_coupens';")
        
        # 2. Drop tables
        tables = [
            "plans_coupens_providerplancapability",
            "plans_coupens_purchasedplan",
            "plans_coupens_plancapability", # might not exist
            "plans_coupens_planprice",
            "plans_coupens_coupon_applies_to_plans",
            "plans_coupens_coupon",
            "plans_coupens_plan",
            "plans_coupens_billingcycle",
            # Old tables
            "plans_coupens_providerplanpermission",
            "plans_coupens_planitem_facilities",
            "plans_coupens_planitem",
        ]
        
        print("Dropping tables...")
        for table in tables:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                print(f"Dropped {table}")
            except Exception as e:
                print(f"Error dropping {table}: {e}")

if __name__ == "__main__":
    reset_app()
