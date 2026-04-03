import psycopg2
import uuid

# Database connection details
DB_PARAMS = {
    "dbname": "provider_db",
    "user": "petleo",
    "password": "petleo",
    "host": "127.0.0.1",
    "port": "5432"
}

# Target User: anil.naga@ibridge.digital
USER_AUTH_ID = "0bff4c7a-40cf-4471-aab1-9d036da2e0ec"
SYSTEM_ADMIN_ID = "550e8400-e29b-41d4-a716-446655440000"

CATEGORIES = [
    ("550e8400-e29b-41d4-a716-446655440001", "Employee Management", "EMPLOYEE_MANAGEMENT"),
    ("550e8400-e29b-41d4-a716-446655440002", "Role Management", "ROLE_MANAGEMENT"),
    ("550e8400-e29b-41d4-a716-446655440003", "Customer Booking Management", "CUSTOMER_BOOKING"),
    ("550e8400-e29b-41d4-a716-446655440004", "Clinic Management", "CLINIC_MANAGEMENT"),
]

def run_sql():
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()

        # 1. Ensure System Management Service Template exists
        cur.execute("""
            INSERT INTO provider_dynamic_fields_providertemplateservice (id, super_admin_service_id, name, display_name, icon, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (super_admin_service_id) DO UPDATE SET 
                name = EXCLUDED.name, 
                display_name = EXCLUDED.display_name, 
                icon = EXCLUDED.icon,
                updated_at = NOW()
            RETURNING id;
        """, (str(uuid.uuid4()), SYSTEM_ADMIN_ID, "SYSTEM_ADMIN", "System Management", "tabler-settings"))
        service_uuid = cur.fetchone()[0]
        print(f"Service Template 'System Management' (ID: {SYSTEM_ADMIN_ID}) ready.")

        # 2. Grant Service Level Permission
        cur.execute("""
            INSERT INTO provider_dynamic_fields_providercapabilityaccess (id, user_id, plan_id, service_id, category_id, facility_id, pricing_id, can_view, can_create, can_edit, can_delete, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NULL, NULL, NULL, TRUE, TRUE, TRUE, TRUE, NOW(), NOW())
            ON CONFLICT (user_id, plan_id, service_id, category_id, facility_id, pricing_id) DO UPDATE SET
                can_view = TRUE, can_create = TRUE, can_edit = TRUE, can_delete = TRUE, updated_at = NOW();
        """, (str(uuid.uuid4()), USER_AUTH_ID, "FULL_ACCESS", SYSTEM_ADMIN_ID))
        print(f"Service Level Access granted for {USER_AUTH_ID}.")

        # 3. Handle Categories
        for cat_id, cat_name, linked_cap in CATEGORIES:
            # Ensure Category Template exists
            cur.execute("""
                INSERT INTO provider_dynamic_fields_providertemplatecategory (id, super_admin_category_id, service_id, name, description, linked_capability, duration_minutes, base_price, execution_mode, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 60, 0.00, 'SEQUENTIAL', NOW(), NOW())
                ON CONFLICT (super_admin_category_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    linked_capability = EXCLUDED.linked_capability,
                    updated_at = NOW();
            """, (str(uuid.uuid4()), cat_id, service_uuid, cat_name, f"Manage {cat_name.lower()}", linked_cap))
            
            # Grant Permission
            cur.execute("""
                INSERT INTO provider_dynamic_fields_providercapabilityaccess (id, user_id, plan_id, service_id, category_id, facility_id, pricing_id, can_view, can_create, can_edit, can_delete, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NULL, NULL, TRUE, TRUE, TRUE, TRUE, NOW(), NOW())
                ON CONFLICT (user_id, plan_id, service_id, category_id, facility_id, pricing_id) DO UPDATE SET
                    can_view = TRUE, can_create = TRUE, can_edit = TRUE, can_delete = TRUE, updated_at = NOW();
            """, (str(uuid.uuid4()), USER_AUTH_ID, "FULL_ACCESS", SYSTEM_ADMIN_ID, cat_id))
            print(f"  - Category '{cat_name}' (Cap: {linked_cap}) granted.")

        conn.commit()
        cur.close()
        conn.close()
        print("\n✅ System Management Access (Raw SQL) Granted.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_sql()
