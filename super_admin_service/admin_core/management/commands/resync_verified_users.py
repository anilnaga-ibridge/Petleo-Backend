import os
import django
from django.core.management.base import BaseCommand
from django.db import connections
from admin_core.models import VerifiedUser

class Command(BaseCommand):
    help = 'Resync VerifiedUser table from Auth_Service database'

    def handle(self, *args, **options):
        # We use raw SQL to fetch from Auth_Service
        # This assumes the same Postgres server and access-granted
        
        # fallback: use the JSON I already exported if it exists
        json_path = "/Users/PraveenWorks/Anil Works/Petleo-Backend/Auth_Service/auth_service/users_backfill.json"
        
        if os.path.exists(json_path):
            import json
            with open(json_path, 'r') as f:
                users_data = json.load(f)
            
            count = 0
            for auth_id, details in users_data.items():
                user, created = VerifiedUser.objects.update_or_create(
                    auth_user_id=auth_id,
                    defaults={
                        "email": details.get("email"),
                        "full_name": details.get("full_name"),
                        "phone_number": details.get("phone_number"),
                        "role": details.get("role")
                    }
                )
                if created: count += 1
            
            self.stdout.write(self.style.SUCCESS(f"Successfully synced {len(users_data)} users ({count} new)."))
        else:
            self.stdout.write(self.style.ERROR("users_backfill.json not found. Run export_users.py in Auth_Service first."))
