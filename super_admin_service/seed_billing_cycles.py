import os
import django
import sys

sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from plans_coupens.models import BillingCycleConfig

cycles = [
    {"code": "MONTHLY", "display_name": "Monthly", "duration_days": 30},
    {"code": "YEARLY", "display_name": "Yearly", "duration_days": 365},
    {"code": "WEEKLY", "display_name": "Weekly", "duration_days": 7},
]

for c in cycles:
    obj, created = BillingCycleConfig.objects.get_or_create(
        code=c["code"],
        defaults={
            "display_name": c["display_name"],
            "duration_days": c["duration_days"],
            "is_active": True
        }
    )
    if created:
        print(f"Created {c['code']}")
    else:
        print(f"Exists {c['code']}")
