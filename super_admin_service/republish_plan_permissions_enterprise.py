import os
import json
import sys
import django
import argparse
import logging
from django.utils import timezone

# Setup Django for Super Admin Service
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from plans_coupens.models import PurchasedPlan, Plan
from plans_coupens.kafka_producer import publish_permissions_updated
from plans_coupens.payload_builder import build_unified_payload

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def sync_permissions(email=None, plan_id=None, dry_run=True):
    """
    Triggers a re-sync of permissions for users using the Enterprise Kafka Flow.
    Supports filtering by email or specific plan_id.
    """
    logger.info(f"🚀 Starting Enterprise Permission Sync (Dry Run: {dry_run})")
    
    query = PurchasedPlan.objects.filter(is_active=True)
    if email:
        query = query.filter(user__email=email)
    if plan_id:
        query = query.filter(plan__id=plan_id)
        
    active_plans = query.select_related('user', 'plan')
    count = active_plans.count()
    
    if count == 0:
        logger.warning("⚠️ No active plans found matching the criteria.")
        return

    logger.info(f"📋 Found {count} active plans to sync.")

    for pp in active_plans:
        user = pp.user
        plan = pp.plan
        user_email = getattr(user, 'email', getattr(user, 'username', 'Unknown'))
        auth_id = str(user.auth_user_id) if hasattr(user, 'auth_user_id') else str(user.id)
        
        logger.info(f"🔄 Processing: {user_email} | Plan: {plan.title}")
        
        # Build the new enterprise-grade payload
        data_bundle = build_unified_payload(user, plan, str(pp.id), auth_id)
        
        # Extraction
        event_id = data_bundle.get("event_id")
        schema_version = data_bundle.get("schema_version")
        
        if dry_run:
            logger.info(f"   [DRY RUN] Would emit Event: {event_id} (v{schema_version}) with {len(data_bundle['capabilities'])} capabilities.")
        else:
            # Plan Info metadata
            plan_info = {
                "id": str(pp.id),
                "plan_id": str(plan.id),
                "title": plan.title,
                "start_date": pp.start_date.isoformat(),
                "end_date": pp.end_date.isoformat() if pp.end_date else None,
            }
            
            # Use the existing producer but with the expanded data bundle
            # The producer takes individual components and wraps them in a message.
            # We pass the full data_bundle as part of the 'extra' data or update the producer.
            
            # NOTE: We are reusing publish_permissions_updated but it will now include 
            # the fields we added to the bundle return value.
            
            publish_permissions_updated(
                auth_id, 
                str(pp.id), 
                data_bundle["perms_payload"], # Legacy perms list
                plan_info, 
                templates=data_bundle["templates"], 
                dynamic_capabilities=data_bundle["dynamic_capabilities"]
            )
            logger.info(f"   ✅ Published Event {event_id} for {user_email}")

    logger.info("🏁 Enterprise Sync Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enterprise Permission Re-Sync Tool")
    parser.add_argument("--email", help="Filter by user email")
    parser.add_argument("--plan-id", help="Filter by plan ID")
    parser.add_argument("--run", action="store_true", help="Execute the sync (defaults to dry-run)")
    args = parser.parse_args()
    
    sync_permissions(email=args.email, plan_id=args.plan_id, dry_run=not args.run)
