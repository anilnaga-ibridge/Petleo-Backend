
import os
import sys
import django
import logging

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from plans_coupens.models import ProviderPlanCapability
from dynamic_facilities.models import Facility

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_capabilities():
    logger.info("🔧 Starting Capability Repair...")
    
    # Find capabilities with Facility but missing Service/Category
    broken_caps = ProviderPlanCapability.objects.filter(
        facility__isnull=False
    ).filter(
        models.Q(service__isnull=True) | models.Q(category__isnull=True)
    )
    
    logger.info(f"🔎 Found {broken_caps.count()} broken capabilities.")
    
    count = 0
    for cap in broken_caps:
        fac = cap.facility
        if not fac:
            continue
            
        # Infer from Fac -> Category -> Service
        cat = fac.category
        svc = cat.service if cat else None
        
        updates = []
        if not cap.category and cat:
            cap.category = cat
            updates.append("category")
            
        if not cap.service and svc:
            cap.service = svc
            updates.append("service")
            
        if updates:
            cap.save()
            count += 1
            logger.info(f"✅ Fixed Cap {cap.id} (Fac: {fac.name}): Set {', '.join(updates)}")
            
    logger.info(f"🎉 Repair Complete. Fixed {count} records.")

from django.db import models

if __name__ == "__main__":
    fix_capabilities()
