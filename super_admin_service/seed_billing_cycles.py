import os
import sys
import django

# Add current path and Auth Service paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.abspath(os.path.join(current_dir, '..')))
sys.path.append(os.path.abspath(os.path.join(current_dir, '..', 'Auth_Service', 'auth_service')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from plans_coupens.models import BillingCycleConfig

def seed_billing_cycles():
    cycles = [
        {
            "code": "MONTHLY",
            "display_name": "Monthly",
            "duration_days": 30,
            "is_active": True
        },
        {
            "code": "YEARLY",
            "display_name": "Yearly",
            "duration_days": 365,
            "is_active": True
        },
        {
            "code": "QUARTERLY",
            "display_name": "Quarterly",
            "duration_days": 90,
            "is_active": True
        }
    ]

    print("🌱 Seeding Billing Cycles...")
    for cycle_data in cycles:
        obj, created = BillingCycleConfig.objects.update_or_create(
            code=cycle_data["code"],
            defaults=cycle_data
        )
        if created:
            print(f"✅ Created: {obj.code}")
        else:
            print(f"🔄 Updated: {obj.code}")
    print("✨ Seeding complete.")

if __name__ == "__main__":
    seed_billing_cycles()
