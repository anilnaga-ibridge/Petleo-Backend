
import os
import django
import uuid
import sys

auth_user_id = "5ee51be1-7065-43e0-898a-2dca34dd3820"
# Use the avatar I saw in the ServiceProvider model earlier
avatar_relative = "provider_avatars/Photo_on_06-02-26_at_5_otnpacQ.50PM.jpeg"
avatar_absolute = f"http://127.0.0.1:8002/media/{avatar_relative}"

try:
    # 1. Update Auth Service DB
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Auth_Service', 'auth_service')))
    os.environ["DJANGO_SETTINGS_MODULE"] = "auth_service.settings"
    django.setup()
    
    from users.models import User
    user = User.objects.get(id=uuid.UUID(auth_user_id))
    user.avatar_url = avatar_absolute
    user.save()
    print(f"✅ Auth Service DB updated: {avatar_absolute}")
    
    # 2. Publish Kafka Event (this is the key for syncing to Super Admin)
    from users.kafka_producer import publish_event
    publish_event(
        event_type="USER_UPDATED",
        data={
            "auth_user_id": auth_user_id,
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "role": user.role.name.lower() if user.role else "organization",
            "avatar_url": avatar_absolute,
        }
    )
    print("✅ Kafka event published manually from Auth Service.")

except Exception as e:
    print(f"❌ Error during manual sync: {e}")
