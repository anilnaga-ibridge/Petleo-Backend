import os
import django
import sys
import psycopg2

# Setup SA
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()
from dynamic_fields.models import ProviderDocumentVerification
from admin_core.models import VerifiedUser

def sync():
    # Connect to SP Database
    sp_conn = psycopg2.connect(dbname="provider_db", user="petleo", password="petleo", host="127.0.0.1")
    cur = sp_conn.cursor()
    
    # 1. Fetch ALL documents from SP
    cur.execute("SELECT id, verified_user_id, definition_id, file, filename, status FROM provider_dynamic_fields_providerdocument")
    rows = cur.fetchall()
    
    print(f"Found {len(rows)} documents in Service Provider DB.")
    
    count = 0
    for row in rows:
        doc_id, provider_id, definition_id, file_path, filename, status = row
        
        # 2. Ensure Provider exists in SA VerifiedUser table
        if not VerifiedUser.objects.filter(auth_user_id=provider_id).exists():
            print(f"  Provider {provider_id} missing in SA. Syncing from SP...")
            cur2 = sp_conn.cursor()
            cur2.execute("SELECT email, full_name, phone_number FROM service_provider_verifieduser WHERE auth_user_id = %s", (provider_id,))
            user_row = cur2.fetchone()
            
            if user_row:
                email, full_name, phone_number = user_row
                VerifiedUser.objects.create(
                    auth_user_id=provider_id,
                    email=email,
                    full_name=full_name,
                    phone_number=phone_number,
                    role='provider'
                )
                print(f"    - Created VerifiedUser: {full_name}")
            else:
                # Create dummy if not in SP verified users either (should be rare)
                VerifiedUser.objects.create(
                    auth_user_id=provider_id,
                    email=f"unknown_{provider_id}@placeholder.com",
                    full_name=f"Unknown Provider ({provider_id})",
                    role='provider'
                )
                print(f"    - Created DUMMY VerifiedUser for {provider_id}")
            
        # 3. Create/Update Document in SA
        obj, created = ProviderDocumentVerification.objects.update_or_create(
            document_id=doc_id,
            defaults={
                "auth_user_id": provider_id,
                "definition_id": definition_id,
                "file_url": f"/media/{file_path}",
                "filename": filename,
                "status": status.lower()
            }
        )
        if created: count += 1
        print(f"  - Synced Document: {filename}")
    
    print(f"\nSUCCESS: Synced {len(rows)} documents total ({count} new).")
    sp_conn.close()

if __name__ == "__main__":
    sync()
