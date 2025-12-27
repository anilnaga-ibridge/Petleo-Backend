import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderTemplateService
from service_provider.views import _build_permission_tree

def verify_discrepancy():
    print("--- Verifying Service Discrepancy ---")
    
    user = VerifiedUser.objects.filter(email='ram@gmail.com').first()
    if not user:
        print("User not found")
        return

    print(f"User: {user.email}")

    # 1. Plan Services (Source of Truth: ProviderTemplateService)
    # These are synced from SuperAdmin when the plan is purchased.
    all_templates = ProviderTemplateService.objects.all()
    print(f"\n[PLAN] Total Services in DB (Templates): {all_templates.count()}")
    for t in all_templates:
        print(f" - {t.display_name} ({t.super_admin_service_id})")

    # 2. Frontend Services (What the UI sees)
    # This comes from _build_permission_tree
    frontend_tree = _build_permission_tree(user)
    print(f"\n[FRONTEND] Total Services in Dashboard: {len(frontend_tree)}")
    
    frontend_ids = set()
    for svc in frontend_tree:
        frontend_ids.add(svc['service_id'])
        print(f" - {svc['service_name']} ({svc['service_id']})")
        # Check visibility
        if not svc['can_view']:
            print(f"   WARNING: Service exists but can_view=False (Hidden in UI?)")

    # 3. Comparison
    print("\n--- Comparison ---")
    missing_in_frontend = []
    for t in all_templates:
        if t.super_admin_service_id not in frontend_ids:
            missing_in_frontend.append(t.display_name)
    
    if missing_in_frontend:
        print(f"❌ MISSING IN FRONTEND: {missing_in_frontend}")
    else:
        print("✅ ALL Plan Services are visible in Frontend.")

if __name__ == "__main__":
    verify_discrepancy()
