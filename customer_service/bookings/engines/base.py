from abc import ABC, abstractmethod
from decimal import Decimal

class BaseEngine(ABC):
    """
    Abstract Base Class for all Booking Engines (Protocols).
    Each engine defines how to validate availability and calculate price.
    """
    
    def __init__(self, pricing_rule_snapshot):
        self.config = pricing_rule_snapshot
        self.duration_type = self.config.get('service_duration_type')
        self.pricing_model = self.config.get('pricing_model')
        self.base_price = Decimal(str(self.config.get('base_price', 0)))

    @abstractmethod
    def validate_availability(self, item_data):
        """
        Check if the requested slot/date/quantity is available.
        Should raise a ValidationError if not available.
        """
        pass

    @abstractmethod
    def calculate_price(self, item_data):
        """
        Return the total price for this specific booking item.
        """
        pass

    def get_context_snapshot(self):
        """
        Returns relevant logic snapshot for forensic auditing.
        """
        return {
            "duration_type": self.duration_type,
            "pricing_model": self.pricing_model,
            "base_price": float(self.base_price)
        }
