import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from users.models import User

data = {}
for user in User.objects.all():
    data[str(user.id)] = {
        "email": user.email,
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "role": user.role.name.lower() if user.role else "user"
    }

with open("users_backfill.json", "w") as f:
    json.dump(data, f, indent=4)

print(f"Exported {len(data)} users to users_backfill.json")
