from .base import BaseEngine
from decimal import Decimal
from rest_framework.exceptions import ValidationError
from datetime import datetime

class DayEngine(BaseEngine):
    """
    Engine for DAYS (Date/Range) based services.
    Handles Daycare (single day) and Boarding (range).
    """
    
    def validate_availability(self, item_data):
        selected_time = item_data.get('selected_time')
        end_time = item_data.get('end_time') # Optional for range
        
        if not selected_time:
            raise ValidationError("A start date is required for day-based services.")

        # Real capacity logic would check the daily_capacity field
        # against existing bookings for EVERY day in the range.
        return True

    def calculate_price(self, item_data):
        start_date = item_data.get('selected_time')
        end_date = item_data.get('end_time')
        
        # Default to 1 day if no end date provided
        days = 1
        if end_date and isinstance(end_date, datetime) and isinstance(start_date, datetime):
            delta = end_date.date() - start_date.date()
            days = max(delta.days, 1) # Min 1 day

        if self.pricing_model == 'DAILY':
            return self.base_price * Decimal(str(days))
            
        if self.pricing_model == 'WEEKLY':
            weeks = Decimal(str(days)) / Decimal('7')
            return self.base_price * weeks

        return self.base_price # FIXED price for the stay
