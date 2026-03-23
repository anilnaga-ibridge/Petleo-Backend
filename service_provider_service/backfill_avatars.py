import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser

# Map of email to avatar_url found in Auth Service
AVATAR_MAP = {
    'anil.naga@ibridge.digital': 'http://127.0.0.1:8002/media/provider_avatars/Photo_on_06-02-26_at_5_otnpacQ.50PM.jpeg',
    'gopi@gmail.com': 'http://127.0.0.1:8002/media/provider_avatars/Photo_on_06-02-26_at_2_JWMzCUA.21PM.jpeg',
    'rahull@gmail.com': 'http://127.0.0.1:8002/media/provider_avatars/Photo_on_13-02-26_at_10_4cPzNSU.47AM.jpeg',
    'raj@gmail.com': 'http://127.0.0.1:8002/media/provider_avatars/Photo_on_06-02-26_at_2_O7BRDkR.21PM.jpeg',
    'superadmin.manual@petleo.com': 'http://127.0.0.1:8002/media/provider_avatars/Photo_on_06-02-26_at_2_FxOizA5.21PM.jpeg',
}

def backfill():
    count = 0
    for email, url in AVATAR_MAP.items():
        updated = VerifiedUser.objects.filter(email=email).update(avatar_url=url)
        if updated:
            print(f"✅ Updated {email}")
            count += 1
        else:
            print(f"⚠️ User {email} not found in Service Provider service.")
    
    print(f"\nSuccessfully backfilled {count} avatars.")

if __name__ == '__main__':
    backfill()
