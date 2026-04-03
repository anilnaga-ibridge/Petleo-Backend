import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime
import sys

# DATABASE CONFIGURATIONS
PROVIDER_DB = {
    'dbname': 'provider_db',
    'user': 'postgres',
    'password': 'postgres',
    'host': '127.0.0.1',
    'port': '5434'
}

# PRE-VERIFIED DEFINITIVE IDS FOR PLATINUM PLAN (PROD-DB IDs)
DEFINITIVE_CAPABILITIES = [
    # --- BOARDING ---
    {'service_id': '5fc04df6-72aa-4c81-801a-8215582f3ec3', 'category_id': '1da7f7ab-ba8a-4aa6-b50b-da83122a5559', 'facility_id': 'e0670f63-188c-4a3a-bf48-5560cf874cc8'}, # Food + stay Node
    
    # --- GROOMING ---
    {'service_id': 'f343467f-9457-4183-bd08-f98647acae4d', 'category_id': '8da8985a-1697-4e20-8cbc-9917af43c168', 'facility_id': '7df04028-0c60-4b6d-ac59-17069dddf1ac'}, # Bathing Node
    
    # --- VETERINARY HUB ---
    {'service_id': 'da615467-3c61-4c03-ac9b-c3c0894d97e7', 'category_id': 'f32478b6-f6de-49ad-9600-32c49229bd80', 'facility_id': None}, # Visits
    {'service_id': 'da615467-3c61-4c03-ac9b-c3c0894d97e7', 'category_id': 'd5292522-e77d-4d16-9b0d-8b33a750a191', 'facility_id': None}, # Patients
    {'service_id': 'da615467-3c61-4c03-ac9b-c3c0894d97e7', 'category_id': 'ed26c9c7-e469-47e1-bc59-bfd3f9aea91f', 'facility_id': None}, # Veterinary Assistant
    {'service_id': 'da615467-3c61-4c03-ac9b-c3c0894d97e7', 'category_id': '83ca5de4-cce5-4567-a811-e2413c753fc7', 'facility_id': None}, # Doctor Station
    {'service_id': 'da615467-3c61-4c03-ac9b-c3c0894d97e7', 'category_id': '6a9c6829-d1d1-48ae-ad3d-ec48f130ec34', 'facility_id': None}, # Pharmacy
    {'service_id': 'da615467-3c61-4c03-ac9b-c3c0894d97e7', 'category_id': '322e7aa6-aa85-4b90-9e7e-0f35ee136db7', 'facility_id': None}, # Veterinary Core
]

def sync_provider_permissions(email):
    print(f"\n🚀 [DEFINITIVE SYNC] Restoring Platinum Hub for: {email}")
    
    try:
        conn_p = psycopg2.connect(**PROVIDER_DB)
        cur_p = conn_p.cursor(cursor_factory=RealDictCursor)

        # 1. Get User Profile
        cur_p.execute("SELECT id, auth_user_id FROM verified_users WHERE email = %s", (email,))
        provider_user = cur_p.fetchone()
        
        if not provider_user:
            print(f"❌ User {email} not found!")
            return

        vu_id = provider_user['id']
        auth_user_id = provider_user['auth_user_id']

        # 2. Sync Plan Access (PCA Table)
        # PCA user_id references verified_users.auth_user_id
        cur_p.execute("DELETE FROM provider_dynamic_fields_providercapabilityaccess WHERE user_id = %s", (auth_user_id,))
        
        for cap in DEFINITIVE_CAPABILITIES:
            cur_p.execute("""
                INSERT INTO provider_dynamic_fields_providercapabilityaccess 
                (id, user_id, plan_id, service_id, category_id, facility_id, can_view, can_create, can_edit, can_delete, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                str(uuid.uuid4()), 
                auth_user_id, 
                'PLATINUM-PLAN-ID',
                cap['service_id'],
                cap['category_id'],
                cap['facility_id'],
                True, True, True, True, 
                datetime.now(), datetime.now()
            ))
        
        print(f"✅ Synced {len(DEFINITIVE_CAPABILITIES)} facility-aware capability nodes.")

        # 3. Ensure AllowedService entries exist
        # AllowedService verified_user_id references verified_users.id (PK)
        cur_p.execute("DELETE FROM service_provider_allowedservice WHERE verified_user_id = %s", (vu_id,))
        
        service_ids = set(cap['service_id'] for cap in DEFINITIVE_CAPABILITIES)
        for s_id in service_ids:
            cur_p.execute("""
                INSERT INTO service_provider_allowedservice 
                (id, verified_user_id, service_id, name, icon, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (str(uuid.uuid4()), vu_id, s_id, "Platinum Service Hub", "tabler-box", datetime.now()))
        
        print(f"✅ Registered {len(service_ids)} allowed service hubs.")

        conn_p.commit()
        print(f"🎉 DEFINITIVE Restoration complete for {email}!\n")

    except Exception as e:
        print(f"❌ Error during sync: {e}")
        if 'conn_p' in locals(): conn_p.rollback()
    finally:
        if 'conn_p' in locals(): conn_p.close()

if __name__ == "__main__":
    emails = sys.argv[1:] if len(sys.argv) > 1 else ['madhu@gmail.com', 'nagaanil29@gmail.com']
    for email in emails:
        sync_provider_permissions(email)
