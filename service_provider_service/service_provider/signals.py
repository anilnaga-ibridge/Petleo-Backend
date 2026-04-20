
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from .models import OrganizationEmployee, ProviderRole, ProviderRoleCapability, VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess


@receiver([post_save, post_delete], sender=OrganizationEmployee)
def publish_workforce_snapshot(sender, instance, **kwargs):
    """
    Publish a workforce pulse to Kafka when staff count changes.
    Consumed by Super Admin for global analytics.
    """
    from service_provider.kafka_producer import publish_event
    import logging
    logger = logging.getLogger(__name__)

    try:
        org = instance.organization
        total_employees = org.employees.filter(status='ACTIVE').count()
        
        event_data = {
            "organization_id": str(org.id),
            "organization_name": org.legal_name,
            "employee_count": total_employees,
            "updated_at": timezone.now().isoformat()
        }

        publish_event("PROVIDER.WORKFORCE.SNAPSHOT", event_data)
        logger.info(f"📡 Published workforce snapshot for {org.legal_name}: {total_employees} staff")
    except Exception as e:
        logger.error(f"❌ Failed to publish workforce snapshot: {e}")

@receiver([post_save, post_delete], sender=OrganizationEmployee)
def invalidate_employee_cache(sender, instance, **kwargs):
    """Invalidate cache when employee record changes (e.g. role assigned)."""
    instance.invalidate_permission_cache()

@receiver([post_save, post_delete], sender=ProviderRole)
def invalidate_role_employees_cache(sender, instance, **kwargs):
    """Invalidate cache for all employees assigned to this role."""
    for employee in instance.employees.all():
        employee.invalidate_permission_cache()

@receiver([post_save, post_delete], sender=ProviderRoleCapability)
def invalidate_role_cap_employees_cache(sender, instance, **kwargs):
    """Invalidate cache for all employees when role capabilities change."""
    role = instance.provider_role
    for employee in role.employees.all():
        employee.invalidate_permission_cache()

@receiver([post_save, post_delete], sender=ProviderCapabilityAccess)
def invalidate_org_employees_cache(sender, instance, **kwargs):
    """Invalidate cache for all employees in an organization when plan/capabilities change."""
    # instance.user is the VerifiedUser (Organization Owner)
    # We need to find the ServiceProvider profile and then its employees.
    try:
        provider_profile = instance.user.provider_profile
        for employee in provider_profile.employees.all():
            employee.invalidate_permission_cache()
    except Exception:
        # If no profile yet or other issue, skip
        pass
@receiver(post_save, sender=VerifiedUser)
def sync_provider_type(sender, instance, created, **kwargs):
    """
    Ensure ServiceProvider.provider_type matches VerifiedUser.role.
    This fixes inconsistencies where Organization users appear as Individuals.
    """
    if not instance.role:
        return

    from service_provider.models import ServiceProvider

    role_lower = instance.role.lower()
    target_type = None

    if role_lower in ['organization', 'serviceprovider', 'service_provider']:
        target_type = 'ORGANIZATION'
    elif role_lower in ['individual', 'provider']:
        target_type = 'INDIVIDUAL'
    
    if target_type:
        # Get or create provider profile
        provider, _ = ServiceProvider.objects.get_or_create(verified_user=instance)
        
        if provider.provider_type != target_type:
            provider.provider_type = target_type
            provider.save()
            print(f"🔄 [Signal] Auto-corrected provider_type to {target_type} for {instance.email}")
