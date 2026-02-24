
import psycopg2
import uuid
import datetime

# DB Config
DB_HOST = "localhost"
DB_PORT = "5432"
DB_USER = "petleo"
DB_PASSWORD = "petleo"

SA_DB = "Super_Admin"
AUTH_DB = "Auth_Service"

def run_sync():
    print("🚀 Starting Raw SQL Debug & Sync...")

    try:
        # 1. Connect to Super Admin DB
        sf_conn = psycopg2.connect(dbname=SA_DB, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        sf_cur = sf_conn.cursor()
        
        # 2. Get Latest Verification
        print("🔍 Checking latest verification in Super_Admin...")
        sf_cur.execute("SELECT id, auth_user_id, filename, created_at FROM dynamic_fields_providerdocumentverification ORDER BY created_at DESC LIMIT 1;")
        latest = sf_cur.fetchone()
        
        if not latest:
            print("❌ No verifications found.")
            return

        doc_id, auth_user_id, filename, created_at = latest
        print(f"📄 Latest Doc: {filename} (ID: {doc_id})")
        print(f"   AuthUserID: {auth_user_id}")
        
        # 3. Check VerifiedUser
        sf_cur.execute("SELECT id, email, full_name, role FROM verified_users WHERE auth_user_id = %s", (str(auth_user_id),))
        verified_user = sf_cur.fetchone()
        
        if verified_user:
            print(f"✅ VerifiedUser FOUND: {verified_user[1]} (Role: {verified_user[3]})")
            print("   The issue might be frontend specific or cache if data is correct here.")
            return
        else:
            print("❌ VerifiedUser MISSING! Attempting to sync from Auth Service...")
            
        # 4. Fetch from Auth Service
        auth_conn = psycopg2.connect(dbname=AUTH_DB, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        auth_cur = auth_conn.cursor()
        
        auth_cur.execute("SELECT id, email, full_name, phone_number, role FROM users_user WHERE id = %s", (str(auth_user_id),))
        auth_user = auth_cur.fetchone()
        
        auth_cur.close()
        auth_conn.close()
        
        if not auth_user:
            print("❌ User NOT FOUND in Auth Service either! This is a ghost record.")
            return
            
        print(f"✅ Found in Auth Service: {auth_user[1]} ({auth_user[2]})")
        
        # 5. Insert into VerifiedUser
        print("📥 Inserting into verified_users...")
        new_id = str(uuid.uuid4())
        # Assuming table columns: id, auth_user_id, full_name, email, phone_number, role, permissions (json), created_at, updated_at, avatar_url
        # We need to verify column count/names or use named insert if possible (psycopg2 is positional mostly)
        
        # Let's simple try basic fields
        query = """
        INSERT INTO verified_users (id, auth_user_id, email, full_name, phone_number, role, permissions, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, '[]', NOW(), NOW());
        """
        sf_cur.execute(query, (new_id, str(auth_user[0]), auth_user[1], auth_user[2], auth_user[3], auth_user[4]))
        sf_conn.commit()
        
        print("🎉 Successfully inserted VerifiedUser!")
        
        sf_cur.close()
        sf_conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_sync()
