import os
import django
from django.db import connections

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from dynamic_fields.models import ProviderDocumentVerification

# IDs mentioned by the user as 404s
orphaned_ids = ['ed7b14c7-158e-4be5-8716-34020cd8132a', '72fe5b78-879a-4db5-adb5-c4b1766ffa18']

deleted_count, _ = ProviderDocumentVerification.objects.filter(auth_user_id__in=orphaned_ids).delete()

print(f"Deleted {deleted_count} orphaned verification records.")

# Also delete any others where definition_id is null AND provider_name is 'Unknown Provider'
others = ProviderDocumentVerification.objects.filter(definition_id__isnull=True)
count = 0
for doc in others:
    # Double check if provider exists
    from admin_core.models import VerifiedUser
    if not VerifiedUser.objects.filter(auth_user_id=doc.auth_user_id).exists():
        doc.delete()
        count += 1

print(f"Deleted {count} other orphaned/stale records.")
