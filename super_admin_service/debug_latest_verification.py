
import os
import sys
import django

# Setup minimal Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Auth_Service')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')

try:
    django.setup()
except Exception as e:
    print(f"Warning during django.setup(): {e}")

from dynamic_fields.models import ProviderDocumentVerification
from admin_core.models import VerifiedUser

def check_latest():
    print('🔍 Checking latest verification...')
    latest = ProviderDocumentVerification.objects.first() # Meta ordering is -created_at
    
    if not latest:
        print("❌ No verification documents found.")
        return

    print(f"📄 Latest Document ID: {latest.id}")
    print(f"   Auth User ID: {latest.auth_user_id}")
    print(f"   Filename: {latest.filename}")
    print(f"   Created At: {latest.created_at}")
    
    user_exists = VerifiedUser.objects.filter(auth_user_id=latest.auth_user_id).exists()
    if user_exists:
        user = VerifiedUser.objects.get(auth_user_id=latest.auth_user_id)
        print(f"✅ VerifiedUser FOUND: {user.email} (Role: {user.role})")
    else:
        print("❌ VerifiedUser MISSING for this auth_user_id!")
        print("   -> This explains 'Unknown Provider'")

if __name__ == '__main__':
    check_latest()
