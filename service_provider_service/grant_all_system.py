import psycopg2
import uuid

DB_PARAMS = {
    "dbname": "provider_db",
    "user": "petleo",
    "password": "petleo",
    "host": "127.0.0.1",
    "port": "5432"
}

SYSTEM_ADMIN_ID = "550e8400-e29b-41d4-a716-446655440000"
CATEGORIES = [
    ("550e8400-e29b-41d4-a716-446655440001", "Employee Management", "EMPLOYEE_MANAGEMENT"),
    ("550e8400-e29b-41d4-a716-446655440002", "Role Management", "ROLE_MANAGEMENT"),
    ("550e8400-e29b-41d4-a716-446655440003", "Customer Booking Management", "CUSTOMER_BOOKING"),
    ("550e8400-e29b-41d4-a716-446655440004", "Clinic Management", "CLINIC_MANAGEMENT"),
]

def grant_all():
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()

        # 1. Get all Organization Users
        cur.execute("SELECT auth_user_id, email, id FROM verified_users WHERE role = 'organization';")
        users = cur.fetchall()
        print(f"Found {len(users)} organization users.")

        # 2. Ensure Service Template
        cur.execute("""
            INSERT INTO provider_dynamic_fields_providertemplateservice (id, super_admin_service_id, name, display_name, icon, created_at, updated_at)
            VALUES (%s, %s, 'SYSTEM_ADMIN', 'System Management', 'tabler-settings', NOW(), NOW())
            ON CONFLICT (super_admin_service_id) DO NOTHING;
        """, (str(uuid.uuid4()), SYSTEM_ADMIN_ID))

        # Get the UUID of the service
        cur.execute("SELECT id FROM provider_dynamic_fields_providertemplateservice WHERE super_admin_service_id = %s;", (SYSTEM_ADMIN_ID,))
        service_uuid = cur.fetchone()[0]

        # 3. Ensure Category Templates
        for cat_id, cat_name, linked_cap in CATEGORIES:
            cur.execute("""
                INSERT INTO provider_dynamic_fields_providertemplatecategory (id, super_admin_category_id, service_id, name, description, linked_capability, duration_minutes, base_price, execution_mode, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 60, 0.00, 'SEQUENTIAL', NOW(), NOW())
                ON CONFLICT (super_admin_category_id) DO NOTHING;
            """, (str(uuid.uuid4()), cat_id, service_uuid, cat_name, f"Manage {cat_name.lower()}", linked_cap))

        # 4. Grant to each user
        for auth_id, email, pk_id in users:
            print(f"Granting to {email}...")
            
            # Service Level
            cur.execute("""
                INSERT INTO provider_dynamic_fields_providercapabilityaccess (id, user_id, plan_id, service_id, category_id, facility_id, pricing_id, can_view, can_create, can_edit, can_delete, created_at, updated_at)
                VALUES (%s, %s, 'FULL_ACCESS', %s, NULL, NULL, NULL, TRUE, TRUE, TRUE, TRUE, NOW(), NOW())
                ON CONFLICT (user_id, plan_id, service_id, category_id, facility_id, pricing_id) DO UPDATE SET
                    can_view = TRUE, can_create = TRUE, can_edit = TRUE, can_delete = TRUE, updated_at = NOW();
            """, (str(uuid.uuid4()), auth_id, SYSTEM_ADMIN_ID))

            # Categories
            for cat_id, cat_name, linked_cap in CATEGORIES:
                cur.execute("""
                    INSERT INTO provider_dynamic_fields_providercapabilityaccess (id, user_id, plan_id, service_id, category_id, facility_id, pricing_id, can_view, can_create, can_edit, can_delete, created_at, updated_at)
                    VALUES (%s, %s, 'FULL_ACCESS', %s, %s, NULL, NULL, TRUE, TRUE, TRUE, TRUE, NOW(), NOW())
                    ON CONFLICT (user_id, plan_id, service_id, category_id, facility_id, pricing_id) DO UPDATE SET
                        can_view = TRUE, can_create = TRUE, can_edit = TRUE, can_delete = TRUE, updated_at = NOW();
                """, (str(uuid.uuid4()), auth_id, SYSTEM_ADMIN_ID, cat_id))

            # AllowedService (The UI manifest path)
            cur.execute("""
                INSERT INTO service_provider_allowedservice (id, verified_user_id, service_id, name, icon, created_at)
                VALUES (%s, %s, %s, 'System Management', 'tabler-settings', NOW())
                ON CONFLICT DO NOTHING;
            """, (str(uuid.uuid4()), pk_id, SYSTEM_ADMIN_ID))

        conn.commit()
        cur.close()
        conn.close()
        print("\n✅ All Organization users now have System Management access.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    grant_all()
