from ..models import ServiceProvider, ProviderSubscription
from provider_cart.models import PurchasedPlan

class ProviderService:
    """
    Service layer for provider-related business logic.
    """

    @staticmethod
    def list_active_providers():
        """
        Returns a queryset of active, fully verified ServiceProviders.
        Used by the public marketplace discovery API.
        """
        from ..repositories import ProviderRepository
        return ProviderRepository.get_active_providers_for_marketplace()

    @staticmethod
    def activate_provider_profile(verified_user):
        """
        Ensures a provider is discoverable in the marketplace.
        - Synchronizes PurchasedPlan -> ProviderSubscription
        - Sets profile status to active
        - Sets is_fully_verified to True
        """
        # 1. Sync Subscription
        active_plan = PurchasedPlan.objects.filter(verified_user=verified_user, is_active=True).first()
        if active_plan:
            ProviderSubscription.objects.update_or_create(
                verified_user=verified_user,
                defaults={
                    "plan_id": str(active_plan.plan_id),
                    "start_date": active_plan.start_date,
                    "end_date": active_plan.end_date,
                    "is_active": True,
                    "billing_cycle_id": str(active_plan.billing_cycle_id)
                }
            )

        # 2. Activate Profile
        try:
            sp = ServiceProvider.objects.get(verified_user=verified_user)
            sp.profile_status = 'active'
            sp.is_fully_verified = True
            sp.save()
            return True
        except ServiceProvider.DoesNotExist:
            return False
