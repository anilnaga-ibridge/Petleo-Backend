import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from dynamic_fields.models import ProviderFieldDefinition

def create_fields():
    targets = ["individual", "organization", "employee", "superadmin"]
    
    # Core basic fields
    basic_fields = [
        {"name": "first_name", "label": "First Name", "type": "text", "required": True, "order": 1},
        {"name": "last_name", "label": "Last Name", "type": "text", "required": True, "order": 2},
        {"name": "email", "label": "Email", "type": "text", "required": True, "order": 3},
        {"name": "phone_number", "label": "Phone Number", "type": "text", "required": True, "order": 4},
        {"name": "country", "label": "Country", "type": "text", "required": False, "order": 5},
        {"name": "language", "label": "Language", "type": "text", "required": False, "order": 6},
        {"name": "profile_image", "label": "Profile Picture", "type": "file", "required": False, "order": 7},
    ]

    for target in targets:
        print(f"Creating basic fields for {target}...")
        
        current_fields = basic_fields.copy()
        if target == "organization":
            current_fields.insert(0, {"name": "organization_name", "label": "Organization Name", "type": "text", "required": True, "order": 0})
        
        for f in current_fields:
            obj, created = ProviderFieldDefinition.objects.update_or_create(
                target=target,
                name=f["name"],
                defaults={
                    "label": f["label"],
                    "field_type": f["type"],
                    "is_required": f["required"],
                    "options": f.get("options", []),
                    "order": f.get("order", 0)
                }
            )
            print(f"  {'Created' if created else 'Updated'} {f['name']}")

        # [MODIFIED] Do NOT delete other fields anymore, as super admins can create them dynamically via the UI
        # keep_names = [f["name"] for f in current_fields]
        # deleted_count, _ = ProviderFieldDefinition.objects.filter(target=target).exclude(name__in=keep_names).delete()
        # if deleted_count > 0:
        #    print(f"  Deleted {deleted_count} other non-basic fields for {target}")

if __name__ == "__main__":
    create_fields()
