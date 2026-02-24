
import psycopg2
import os

# DB Config
DB_NAME = "Super_Admin"
DB_USER = "petleo"
DB_PASSWORD = "petleo"
DB_HOST = "localhost"
DB_PORT = "5432"

def cleanup():
    try:
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        
        # 1. Verify VerifiedUser table name
        print("🔍 checking VerifiedUser table...")
        cur.execute("SELECT count(*) FROM verified_users;")
        user_count = cur.fetchone()[0]
        print(f"   Found {user_count} verified users.")
        
        # 2. Verify ProviderDocumentVerification table name (guessing dynamic_fields_providerdocumentverification)
        #    If it fails, we will catch exception
        table_name = "dynamic_fields_providerdocumentverification" 
        
        print(f"🔍 checking {table_name} table...")
        cur.execute(f"SELECT count(*) FROM {table_name};")
        doc_count = cur.fetchone()[0]
        print(f"   Found {doc_count} documents.")
        
        # 3. Perform cleanup
        print("🧹 Performing cleanup...")
        # Check for documents where auth_user_id is NOT in verified_users
        
        query = f"""
            DELETE FROM {table_name}
            WHERE auth_user_id::text NOT IN (
                SELECT auth_user_id FROM verified_users
            );
        """
        cur.execute(query)
        deleted_rows = cur.rowcount
        conn.commit()
        
        print(f"✅ Deleted {deleted_rows} orphaned documents.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    cleanup()
