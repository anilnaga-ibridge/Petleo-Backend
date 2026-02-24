
import os
import sys
import django

# Setup minimal Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Auth_Service')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')

try:
    django.setup()
except Exception as e:
    print(f"Warning during django.setup(): {e}")
    # Proceed even if some apps fail to load, hoping models are loaded enough

from dynamic_fields.models import ProviderDocumentVerification
from admin_core.models import VerifiedUser

def run_cleanup():
    print('Starting cleanup of orphaned verification documents...')
    verifications = ProviderDocumentVerification.objects.all()
    deleted_count = 0
    
    for doc in verifications:
        # Check if User exists
        if not VerifiedUser.objects.filter(auth_user_id=doc.auth_user_id).exists():
            print(f'🗑️ Deleting orphaned document {doc.id} (auth_user_id: {doc.auth_user_id})')
            doc.delete()
            deleted_count += 1
    
    if deleted_count > 0:
        print(f'✅ Successfully deleted {deleted_count} orphaned verification documents.')
    else:
        print('✨ No orphaned documents found. Database is clean.')

if __name__ == '__main__':
    run_cleanup()
