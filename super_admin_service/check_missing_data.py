import os
import django
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from admin_core.models import VerifiedUser
from dynamic_fields.models import ProviderDocumentVerification

print("--- VerifiedUsers ---")
users = VerifiedUser.objects.all()
print(f"Total Users: {users.count()}")
for u in users:
    print(f"ID: {u.auth_user_id} | Email: {u.email} | Name: {u.full_name} | Role: {u.role}")

print("\n--- ProviderDocumentVerifications ---")
docs = ProviderDocumentVerification.objects.all()
print(f"Total Docs: {docs.count()}")
for d in docs:
    print(f"ID: {d.id} | AuthID: {d.auth_user_id} | DefID: {d.definition_id} | Filename: {d.filename} | Status: {d.status}")
