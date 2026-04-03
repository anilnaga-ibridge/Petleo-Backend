
import os
import django
import uuid
import sys

auth_user_id = "5ee51be1-7065-43e0-898a-2dca34dd3820"
# Use the avatar from TODAY (11:33 AM)
avatar_relative = "provider_avatars/Photo_on_06-02-26_at_5_VHdf6m7.50PM.jpeg"
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
    
    # Update Provider Service model as well
    os.environ["DJANGO_SETTINGS_MODULE"] = "service_provider_service.settings"
    django.setup() # Re-setup for different settings
    from service_provider.models import ServiceProvider
    profile = ServiceProvider.objects.get(verified_user__auth_user_id=auth_user_id)
    profile.avatar = avatar_relative
    profile.save()

    # 2. Publish Kafka Event
    os.environ["DJANGO_SETTINGS_MODULE"] = "auth_service.settings"
    django.setup()
    from users.kafka_producer import publish_event
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
    print(f"✅ Synced newer image: {avatar_absolute}")

except Exception as e:
    print(f"❌ Error during manual sync: {e}")
