
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from dynamic_fields.models import ProviderDocumentVerification

print("ID | Auth User ID | Status | Created At")
print("-" * 60)
for doc in ProviderDocumentVerification.objects.all().order_by('-created_at')[:20]:
    print(f"{doc.id} | {doc.auth_user_id} | {doc.status} | {doc.created_at}")
