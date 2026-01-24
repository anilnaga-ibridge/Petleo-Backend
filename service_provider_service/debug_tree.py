
import os
import django
import sys
import json

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser
from service_provider.utils import _build_permission_tree
from service_provider.role_templates import get_role_templates

def debug_tree():
    # Use the known user email or ID often used in these logs
    email = "praveen@gmail.com" # Example, need valid user. Let's try to find one.
    user = VerifiedUser.objects.first()
    if not user:
        print("No users found.")
        return

    print(f"--- Debugging Permission Tree for {user.email} ---")
    tree = _build_permission_tree(user)
    
    for service in tree:
        print(f"Service: {service['service_name']} (Key: {service.get('service_key')})")
        for cat in service.get('categories', []):
            print(f"  - Category: {cat.get('category_name')} (ID: {cat.get('category_id')})")
            
    print("\n--- Debugging Role Templates ---")
    templates = get_role_templates()
    print("Feature Count:", len(templates.get('features', [])))
    for feat in templates.get('features', []):
        print(f"  Feature: {feat.get('title')} ({feat.get('id')})")

if __name__ == '__main__':
    debug_tree()
