from .models import ServiceProvider

class ProviderRepository:
    @staticmethod
    def get_active_providers_for_marketplace():
        """
        Fetches providers that are:
        - Active profile status
        - Fully verified
        - Have an active subscription plan
        """
        return ServiceProvider.objects.filter(
            profile_status='active',
            is_fully_verified=True,
            verified_user__subscription__is_active=True
        ).exclude(
            verified_user__role__iexact='superadmin'
        ).select_related(
            'verified_user', 
            'verified_user__billing_profile'
        ).prefetch_related(
            'verified_user__allowed_services'
        ).distinct()
