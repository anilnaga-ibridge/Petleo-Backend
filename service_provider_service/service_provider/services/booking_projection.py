import json
import logging
import redis
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)

class BookingProjectionService:
    """
    Manages the Redis cache of booking intervals per employee per date.
    This replaces repeated HTTP calls between services.
    Key format: bookings:employee:{employee_id}:{YYYY-MM-DD}
    """
    @staticmethod
    def get_redis_client():
        url = getattr(settings, 'REDIS_URL', 'redis://127.0.0.1:6379/1')
        return redis.Redis.from_url(url)

    @staticmethod
    def _generate_key(employee_id, date_str):
        return f"bookings:employee:{employee_id}:{date_str}"

    @staticmethod
    def get_employee_bookings(employee_id, date_str):
        """
        Fetch bookings from Redis. 
        Returns parsed list of interval dicts or None if cache miss.
        """
        try:
            r = BookingProjectionService.get_redis_client()
            key = BookingProjectionService._generate_key(employee_id, date_str)
            data = r.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error reading booking projection: {e}")
            return None

    @staticmethod
    def add_booking_interval(employee_id, date_str, start_time_str, end_time_str):
        """
        Called when a BOOKING_CREATED event is received.
        Appends the interval and deduplicates.
        """
        try:
            r = BookingProjectionService.get_redis_client()
            key = BookingProjectionService._generate_key(employee_id, date_str)
            
            existing_data = r.get(key)
            intervals = json.loads(existing_data) if existing_data else []
            
            new_interval = {"start": start_time_str, "end": end_time_str}
            if new_interval not in intervals:
                intervals.append(new_interval)
                
            r.set(key, json.dumps(intervals), ex=86400 * 7) # Cache for 7 days
            return True
        except Exception as e:
            logger.error(f"Error adding to booking projection: {e}")
            return False

    @staticmethod
    def remove_booking_interval(employee_id, date_str, start_time_str, end_time_str):
        """
        Called when a BOOKING_CANCELLED event is received.
        """
        try:
            r = BookingProjectionService.get_redis_client()
            key = BookingProjectionService._generate_key(employee_id, date_str)
            
            existing_data = r.get(key)
            if not existing_data:
                return True
                
            intervals = json.loads(existing_data)
            intervals = [i for i in intervals if not (i['start'] == start_time_str and i['end'] == end_time_str)]
            
            r.set(key, json.dumps(intervals), ex=86400 * 7)
            return True
        except Exception as e:
            logger.error(f"Error removing from booking projection: {e}")
            return False
