import json
import logging
from django.core.cache import cache
from django.utils.timezone import is_aware, make_naive

logger = logging.getLogger(__name__)

class AvailabilityCacheService:
    """
    Performance optimization: Caches expensive slot generation results in Redis.
    """
    CACHE_TIMEOUT = 300  # 5 minutes

    @staticmethod
    def _generate_key(employee_id, facility_id, target_date):
        # target_date should be a date object
        date_str = target_date.isoformat() if hasattr(target_date, 'isoformat') else str(target_date)
        return f"slots:{employee_id}:{facility_id}:{date_str}"

    @staticmethod
    def get_slots(employee_id, facility_id, target_date):
        """
        Fetch slots from cache if available, otherwise return None.
        """
        key = AvailabilityCacheService._generate_key(employee_id, facility_id, target_date)
        cached = cache.get(key)
        if cached:
            try:
                return json.loads(cached)
            except Exception as e:
                logger.error(f"Error decoding cached slots: {e}")
        return None

    @staticmethod
    def set_slots(employee_id, facility_id, target_date, slots):
        """
        Store generated slots in cache.
        """
        key = AvailabilityCacheService._generate_key(employee_id, facility_id, target_date)
        try:
            cache.set(key, json.dumps(slots), timeout=AvailabilityCacheService.CACHE_TIMEOUT)
        except Exception as e:
            logger.error(f"Error caching slots: {e}")

    @staticmethod
    def invalidate_slots(employee_id, facility_id, target_date):
        """
        Invalidate cache for a specific employee, facility, and date.
        """
        key = AvailabilityCacheService._generate_key(employee_id, facility_id, target_date)
        cache.delete(key)

    @staticmethod
    def invalidate_employee_day(employee_id, target_date):
        """
        Invalidate ALL services (facility_ids) for an employee on a specific date.
        Uses Redis pattern matching.
        """
        date_str = target_date.isoformat() if hasattr(target_date, 'isoformat') else str(target_date)
        # Pattern: slots:employee_id:*:date_str
        pattern = f"slots:{employee_id}:*:{date_str}"
        
        try:
            # Check if cache has a client (e.g. django-redis)
            if hasattr(cache, 'client') and hasattr(cache.client, 'get_client'):
                client = cache.client.get_client()
                for key in client.scan_iter(pattern):
                    client.delete(key)
            else:
                 # Fallback for simple LocMemCache or non-redis backends
                 # In production we assume Redis
                 pass
        except Exception as e:
            logger.error(f"Error invalidating employee day pattern: {e}")
