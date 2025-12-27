import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, AllowedService, ProviderPermission
from provider_dynamic_fields.models import (
    ProviderCapabilityAccess, 
    ProviderTemplateService, 
    ProviderTemplateCategory, 
    ProviderTemplateFacility, 
    ProviderTemplatePricing
)

def clear_data():
    print("--- Clearing Provider Plan Data ---")
    
    email = 'nagaanil29@gmail.com'
    user = VerifiedUser.objects.filter(email=email).first()
    if not user:
        print(f"User {email} not found")
        return

    print(f"Target User: {user.email} ({user.auth_user_id})")

    # 1. Clear Capabilities (The main permissions)
    deleted_caps, _ = ProviderCapabilityAccess.objects.filter(user=user).delete()
    print(f"Deleted {deleted_caps} ProviderCapabilityAccess records.")

    # 2. Clear Templates (The synced plan structure)
    # Note: Templates are not directly linked to user in the model definition shared earlier?
    # Let's check if they are global or per-user.
    # Looking at models.py: ProviderTemplateService does NOT have a user field.
    # Wait, in kafka_consumer.py, we saw:
    # ProviderTemplateService.objects.all().delete() # This seems to be global or per-provider-db?
    # If this is a microservice with a shared DB, deleting all templates is bad.
    # But if this DB is specific to the provider service and these templates are only for this provider's plan...
    # Let's re-read kafka_consumer.py logic.
    
    # In previous turns, I saw:
    # "ProviderTemplateService.objects.filter(provider=provider).delete()" ?? No, the model didn't have provider.
    # Let's check the model definition again.
    # ProviderTemplateService has NO user/provider FK.
    # This implies the Service Provider Service might be designed where these templates are GLOBAL for the system?
    # OR, the previous code was deleting ALL of them?
    
    # Let's check kafka_consumer.py to see how it handles updates.
    # If I delete them, I might break other users if they share the DB.
    # However, for this specific user/workspace, it seems they are the only one testing.
    # But to be safe, I will only delete Capabilities and AllowedServices first.
    # If the user repurchases, the Kafka consumer will overwrite/update templates anyway.
    
    # Actually, if the user wants to "re-purchase", the most important thing is to clear the "I have this plan" state.
    # That is likely stored in ProviderCapabilityAccess (plan_id) and maybe VerifiedUser.
    
    # 3. Clear Legacy Permissions
    deleted_allowed, _ = AllowedService.objects.filter(verified_user=user).delete()
    print(f"Deleted {deleted_allowed} AllowedService records.")
    
    deleted_perms, _ = ProviderPermission.objects.filter(verified_user=user).delete()
    print(f"Deleted {deleted_perms} ProviderPermission records.")

    print("\n✅ Data cleared. You can now re-purchase the plan.")

if __name__ == "__main__":
    clear_data()
