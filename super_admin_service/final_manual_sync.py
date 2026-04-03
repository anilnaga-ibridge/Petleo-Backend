
import os
import django
import uuid
import sys

auth_user_id = "5ee51be1-7065-43e0-898a-2dca34dd3820"
# Use the avatar from TODAY (11:33 AM)
avatar_relative = "provider_avatars/Photo_on_06-02-26_at_5_VHdf6m7.50PM.jpeg"
avatar_absolute = f"http://127.0.0.1:8002/media/{avatar_relative}"

# --- 1. Update Auth Service ---
os.environ["DJANGO_SETTINGS_MODULE"] = "auth_service.settings"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Auth_Service', 'auth_service')))
django.setup()
from users.models import User
from users.kafka_producer import publish_event

user = User.objects.get(id=uuid.UUID(auth_user_id))
user.avatar_url = avatar_absolute
user.save()

# Trigger the event
publish_event(
    event_type="USER_UPDATED",
    data={
        "auth_user_id": auth_user_id,
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": "organization",
        "avatar_url": avatar_absolute,
    }
)
print(f"✅ Auth and Kafka updated with: {avatar_absolute}")
