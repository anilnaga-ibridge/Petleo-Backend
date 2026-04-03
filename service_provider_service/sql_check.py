import psycopg2

DB_PARAMS = {
    "dbname": "provider_db",
    "user": "petleo",
    "password": "petleo",
    "host": "127.0.0.1",
    "port": "5432"
}

USER_ID = "0bff4c7a-40cf-4471-aab1-9d036da2e0ec"

def check_db():
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()

        print(f"--- Checking System Permissions for {USER_ID} ---")
        
        # 1. Check Service Template
        cur.execute("SELECT id, name, display_name FROM provider_dynamic_fields_providertemplateservice WHERE name = 'SYSTEM_ADMIN';")
        svc = cur.fetchone()
        if svc:
            print(f"✅ Service Template: {svc}")
        else:
            print("❌ Service Template 'SYSTEM_ADMIN' not found.")

        # 2. Check Category Templates
        print("\n--- Category Templates ---")
        cur.execute("SELECT id, name, super_admin_category_id FROM provider_dynamic_fields_providertemplatecategory;")
        cats = cur.fetchall()
        for cat in cats:
            print(f" - {cat}")

        # 3. Check Capability Access
        print("\n--- Capability Access Records ---")
        cur.execute("""
            SELECT service_id, category_id, can_view, can_create, can_edit, can_delete 
            FROM provider_dynamic_fields_providercapabilityaccess 
            WHERE user_id = %s;
        """, (USER_ID,))
        access = cur.fetchall()
        for a in access:
            print(f" - {a}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
