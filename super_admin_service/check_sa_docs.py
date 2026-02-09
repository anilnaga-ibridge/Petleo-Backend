import os
import django
import sys

sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()
from dynamic_fields.models import ProviderDocumentVerification

print(f"SuperAdmin Pending Docs: {ProviderDocumentVerification.objects.filter(status='pending').count()}")
print(f"SuperAdmin Total Docs: {ProviderDocumentVerification.objects.count()}")
for doc in ProviderDocumentVerification.objects.all():
    print(f"  - Doc: {doc.filename}, Provider: {doc.auth_user_id}, Status: {doc.status}")
