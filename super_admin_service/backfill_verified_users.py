import os
import django
import psycopg2
from uuid import UUID

# django setup for Super Admin Service
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from admin_core.models import VerifiedUser

def backfill():
    # Connect to Auth Service Database directly
    try:
        conn = psycopg2.connect(
            dbname="Auth_Service",
            user="petleo",
            password="petleo",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()
        
        # Query users and their roles
        query = """
            SELECT u.id, u.full_name, u.email, u.phone_number, r.name as role_name
            FROM users_user u
            LEFT JOIN users_role r ON u.role_id = r.id
        """
        cur.execute(query)
        rows = cur.fetchall()
        
        print(f"🔍 Found {len(rows)} users in Auth Service.")
        
        count = 0
        for row in rows:
            auth_id, full_name, email, phone, role = row
            
            # Sync to VerifiedUser
            user, created = VerifiedUser.objects.update_or_create(
                auth_user_id=auth_id,
                defaults={
                    "full_name": full_name,
                    "email": email,
                    "phone_number": phone,
                    "role": role.lower() if role else "user",
                }
            )
            count += 1
            action = "Created" if created else "Updated"
            print(f"✅ {action}: {full_name} ({email}) as {role}")

        print(f"🚀 Finished backfilling {count} users.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error during backfill: {e}")

if __name__ == "__main__":
    backfill()
