import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from plans_coupens.models import PurchasedPlan
from plans_coupens.payload_builder import build_unified_payload
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.filter(email__icontains='anil').first()
if not user:
    print("User not found")
    exit()

purchased = PurchasedPlan.objects.filter(user=user).last()
if not purchased:
    print("No purchased plan")
    exit()

print(f"Purchased Plan: {purchased.plan.title}")

bundle = build_unified_payload(user, purchased.plan, str(purchased.id), str(user.id))
perms_payload = bundle['perms_payload']

for p in perms_payload:
    print(f"Service: {p.get('service_name')}, Cat: {p.get('category_name')}, Fac: {p.get('facility_name')}")
    print(f"  View: {p.get('can_view')}, Create: {p.get('can_create')}, Edit: {p.get('can_edit')}, Delete: {p.get('can_delete')}")

