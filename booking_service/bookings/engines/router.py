from .slot_engine import SlotEngine
from .day_engine import DayEngine
from rest_framework.exceptions import ValidationError

class BookingRouter:
    """
    Factory class to route a booking request to the correct Engine.
    """
    
    ENGINE_MAP = {
        'MINUTES': SlotEngine,
        'HOURS': SlotEngine,   # Reuse SlotEngine for Hourly for now
        'DAYS': DayEngine,
        # 'SESSIONS': SessionEngine, # To be implemented
        # 'PRODUCT': ProductEngine,   # To be implemented
    }

    @classmethod
    def get_engine(cls, pricing_rule_snapshot):
        duration_type = pricing_rule_snapshot.get('service_duration_type', 'MINUTES')
        engine_class = cls.ENGINE_MAP.get(duration_type)
        
        if not engine_class:
            # Fallback to SlotEngine or raise error
            return SlotEngine(pricing_rule_snapshot)
            
        return engine_class(pricing_rule_snapshot)
