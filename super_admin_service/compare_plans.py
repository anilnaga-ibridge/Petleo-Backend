import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from plans_coupens.models import Plan

def compare_plans():
    titles = ["Platinum", "Standard Provider Plan"]
    plans = Plan.objects.filter(title__in=titles)
    
    for p in plans:
        print(f"\nPlan: {p.title} (ID: {p.id})")
        caps = p.capabilities.all()
        print(f"Total Capabilities: {caps.count()}")
        
        # Group by service to make it readable
        for c in caps:
            svc = c.service.display_name if c.service else "None"
            cat = c.category.name if c.category else "None"
            fac = c.facility.name if c.facility else "None"
            print(f"  - {svc} > {cat} > {fac}: View={c.can_view}, Create={c.can_create}, Edit={c.can_edit}, Delete={c.can_delete}")

if __name__ == "__main__":
    compare_plans()
