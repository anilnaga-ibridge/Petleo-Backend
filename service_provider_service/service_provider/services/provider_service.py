from ..models import ServiceProvider


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
        return ServiceProvider.objects.filter(
            profile_status='active',
            is_fully_verified=True
        ).select_related('verified_user', 'verified_user__billing_profile')
