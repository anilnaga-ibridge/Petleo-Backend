from .base import BaseEngine
from decimal import Decimal
from rest_framework.exceptions import ValidationError

class SlotEngine(BaseEngine):
    """
    Engine for MINUTES (Slot) based services.
    Typically fixed duration per pet.
    """
    
    def validate_availability(self, item_data):
        selected_time = item_data.get('selected_time')
        if not selected_time:
            raise ValidationError("A specific time slot is required for this service.")
        
        # NOTE: Real availability check would involve querying Employee Shifts
        # and checking for existing BookingItems at this time.
        # For now, we assume capacity is handled by the provider's schedule.
        return True

    def calculate_price(self, item_data):
        # Even if it's "Minutes Based", the pricing model could be FIXED (e.g. ₹500 for haircut)
        # or PER_UNIT (e.g. ₹10 per minute - rare but supported)
        
        if self.pricing_model == 'PER_UNIT':
            duration = Decimal(str(self.config.get('duration_minutes', 0)))
            return self.base_price * duration
            
        return self.base_price  # Default to FIXED total
