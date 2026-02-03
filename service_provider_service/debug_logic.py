
import os
import sys
import django
from django.conf import settings
import uuid

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider.settings") # Adjust settings module
django.setup()

from provider_dynamic_fields.models import ProviderCategory, ProviderTemplateCategory, ProviderTemplateFacility

def test_logic(category_id):
    print(f"Testing for Category ID: {category_id}")
    try:
        real_cat = ProviderCategory.objects.get(id=category_id)
        print(f"Found Real Category: {real_cat.name}, Service ID: {real_cat.service_id}")
        
        # Exact logic from views.py
        t_cat = ProviderTemplateCategory.objects.filter(
             service__super_admin_service_id=real_cat.service_id,
             name=real_cat.name
        ).first()
        
        if t_cat:
            print(f"Found Template Category: {t_cat.name} (ID: {t_cat.id})")
            facs = ProviderTemplateFacility.objects.filter(category=t_cat)
            print(f"Found {facs.count()} facilities:")
            for f in facs:
                print(f" - {f.name}")
        else:
            print("No matching Template Category found via exact match.")
            
            # Try looser match
            t_cat_loose = ProviderTemplateCategory.objects.filter(name__iexact=real_cat.name).first()
            if t_cat_loose:
                 print(f"Found via loose match: {t_cat_loose.name}, Service: {t_cat_loose.service.super_admin_service_id}")
                 if str(t_cat_loose.service.super_admin_service_id) == str(real_cat.service_id):
                     print("Service IDs match!")
                 else:
                     print(f"Service IDs DO NOT match! Real: {real_cat.service_id}, Tmpl: {t_cat_loose.service.super_admin_service_id}")

    except ProviderCategory.DoesNotExist:
        print("Real Category not found!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Bathing ID from previous shell output
    bathing_id = "d30132e9-447b-4c9f-aaa5-b140a5a6929c"
    test_logic(bathing_id)
