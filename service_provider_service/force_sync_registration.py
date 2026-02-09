
import os
import django
import sys
import psycopg2
from uuid import UUID

# Setup Service Provider Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser

def get_auth_data(user_id):
    try:
        conn = psycopg2.connect(
            dbname="Auth_Service",
            user="petleo",
            password="petleo",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()
        cur.execute("SELECT email, full_name, phone_number FROM users_user WHERE id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row
    except Exception as e:
        print(f"Error connecting to Auth_Service: {e}")
        return None

def sync_user(user_id_str):
    print(f"Syncing user {user_id_str} from Registration...")
    
    auth_data = get_auth_data(user_id_str)
    if not auth_data:
        print("Could not find user in registration table.")
        return

    req_email, req_full_name, req_phone = auth_data
    print(f"  Found in Registration: Email={req_email}, Name={req_full_name}, Phone={req_phone}")

    user = VerifiedUser.objects.filter(auth_user_id=user_id_str).first()
    if user:
        user.email = req_email
        user.full_name = req_full_name
        user.phone_number = req_phone
        user.save()
        print("✅ Successfully updated VerifiedUser in provider_db.")
    else:
        print("⚠️ User not found in provider_db.")

if __name__ == "__main__":
    # Current User ID
    current_user_id = "55bdf699-d21f-4cc3-a7b4-65bc37c3394b"
    sync_user(current_user_id)
