
import os
import sys
import django
import psycopg2

# Setup minimal Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Auth_Service')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from admin_core.models import VerifiedUser

# Missing Auth User ID from previous step (will fill after getting output)
# But we can pass it as arg

def sync_user(auth_user_id):
    print(f"🔄 Syncing user {auth_user_id}...")
    
    # 1. Fetch from Auth Service DB (Direct SQL)
    try:
        conn = psycopg2.connect(
            dbname="Auth_Service",
            user="petleo",
            password="petleo",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()
        
        cur.execute("SELECT id, email, full_name, phone_number, role FROM users_user where id = %s", (auth_user_id,))
        row = cur.fetchone()
        
        if row:
            print(f"✅ Found user in Auth Service: {row}")
            # Insert into VerifiedUser
            user, created = VerifiedUser.objects.update_or_create(
                auth_user_id=str(row[0]),
                defaults={
                    "email": row[1],
                    "full_name": row[2],
                    "phone_number": row[3],
                    "role": row[4]
                }
            )
            print(f"🎉 VerifiedUser synced! Created={created}")
        else:
            print("❌ User not found in Auth Service DB!")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error syncing: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manual_sync_user.py <auth_user_id>")
    else:
        sync_user(sys.argv[1])
