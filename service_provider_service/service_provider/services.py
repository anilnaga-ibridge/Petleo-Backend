from .repositories import ProviderRepository

class ProviderService:
    @staticmethod
    def list_active_providers():
        """
        Business logic to retrieve active providers for the marketplace.
        """
        return ProviderRepository.get_active_providers_for_marketplace()
