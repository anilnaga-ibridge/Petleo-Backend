import os
import django
import sys
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/customer_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from bookings.engines.router import BookingRouter
from bookings.engines.slot_engine import SlotEngine
from bookings.engines.day_engine import DayEngine
from rest_framework.exceptions import ValidationError

def test_slot_engine():
    print("\n--- Testing SlotEngine (Minutes) ---")
    config = {
        "service_duration_type": "MINUTES",
        "pricing_model": "PER_UNIT",
        "base_price": 500.00,
        "duration_minutes": 30
    }
    engine = BookingRouter.get_engine(config)
    print(f"Engine class: {engine.__class__.__name__}")
    
    item_data = {
        "selected_time": datetime.now()
    }
    
    # Validation should pass
    engine.validate_availability(item_data)
    
    # Price should be 500 * 30 = 15000 (if per unit is per minute)
    # Wait, in SlotEngine, PER_UNIT * duration_minutes
    price = engine.calculate_price(item_data)
    print(f"Calculated Price (PER_UNIT): {price}")
    
    config["pricing_model"] = "FIXED"
    engine = BookingRouter.get_engine(config)
    price = engine.calculate_price(item_data)
    print(f"Calculated Price (FIXED): {price}")

def test_day_engine():
    print("\n--- Testing DayEngine (Days) ---")
    config = {
        "service_duration_type": "DAYS",
        "pricing_model": "DAILY",
        "base_price": 1000.00
    }
    engine = BookingRouter.get_engine(config)
    print(f"Engine class: {engine.__class__.__name__}")
    
    start = datetime.now()
    end = start + timedelta(days=3)
    
    item_data = {
        "selected_time": start,
        "end_time": end
    }
    
    # 3 days * 1000 = 3000
    price = engine.calculate_price(item_data)
    print(f"Calculated Price (3 Days, DAILY): {price}")
    
    config["pricing_model"] = "FIXED"
    engine = BookingRouter.get_engine(config)
    price = engine.calculate_price(item_data)
    print(f"Calculated Price (3 Days, FIXED): {price}")

if __name__ == "__main__":
    test_slot_engine()
    test_day_engine()
