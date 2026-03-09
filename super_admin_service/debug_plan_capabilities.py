import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from plans_coupens.models import Plan, PlanCapability

plans = Plan.objects.all()
for plan in plans:
    print(f"\nPlan: {plan.title}")
    caps = plan.capabilities.all()
    print(f"Total caps: {caps.count()}")
    for cap in caps:
        svc_name = cap.service.display_name if cap.service else 'None'
        cat_name = cap.category.name if cap.category else 'None'
        fac_name = cap.facility.name if cap.facility else 'None'
        print(f"  Svc: {svc_name}, Cat: {cat_name}, Fac: {fac_name}")
        print(f"    Permissions: {cap.permissions}")

