import os
import django
import uuid

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_service.settings')
django.setup()

from users.models import User
from users.kafka_producer import publish_event

user_id = '81508e5a-1c54-4eda-bc7b-5f2db0b0d775'
user_email = 'kamal@gmail.com'

user = User.objects.filter(id=user_id).first()
if not user:
    print(f"❌ User {user_email} ({user_id}) not found in Auth Service.")
    exit(1)

dynamic_role = user.role.name if user.role else 'organization' # Fallback for test

print(f"🗑️ Deleting user {user_email}...")
# Simulate what UserViewSet.destroy does:
publish_event(
    event_type="USER_DELETED",
    data={
        "auth_user_id": user_id,
        "role": dynamic_role,
    },
)
user.delete()
print(f"✅ User deleted and event published.")
