
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from .models import OrganizationEmployee, ProviderRole, ProviderRoleCapability
from provider_dynamic_fields.models import ProviderCapabilityAccess

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
