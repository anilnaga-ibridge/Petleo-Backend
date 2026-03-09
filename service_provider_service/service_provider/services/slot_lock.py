import logging
import redis
from datetime import timedelta
from django.conf import settings

logger = logging.getLogger(__name__)

class SlotLockService:
    """
    Temporary slot reservation service using Redis.
    Locks a slot for 5 minutes during the checkout/payment flow.
    """
    LOCK_TTL_SECONDS = 300  # 5 minutes

    @staticmethod
    def get_redis_client():
        # Try to use REDIS_URL from settings, fallback to localhost
        url = getattr(settings, 'REDIS_URL', 'redis://127.0.0.1:6379/1')
        return redis.Redis.from_url(url)

    @staticmethod
    def _generate_key(employee_id, service_id, facility_id, start_time, end_time):
        """Identifier based on granular details to prevent conflicts across services."""
        # Convert date objects to strings for the keys
        start_str = start_time.isoformat() if hasattr(start_time, 'isoformat') else str(start_time)
        end_str = end_time.isoformat() if hasattr(end_time, 'isoformat') else str(end_time)
        return f"lock:slot:{employee_id}:{service_id}:{facility_id}:{start_str}:{end_str}"

    @staticmethod
    def lock_slot(employee_id, service_id, facility_id, start_time, end_time):
        """
        Attempt to lock a slot in Redis.
        Returns True if successful, False if already locked.
        """
        try:
            r = SlotLockService.get_redis_client()
            key = SlotLockService._generate_key(employee_id, service_id, facility_id, start_time, end_time)
            
            success = r.set(
                key,
                "locked",
                nx=True,
                ex=SlotLockService.LOCK_TTL_SECONDS
            )
            return bool(success)
        except Exception as e:
            logger.error(f"Error locking slot in Redis: {e}")
            return False

    @staticmethod
    def extend_lock(employee_id, service_id, facility_id, start_time, end_time, new_ttl_seconds=1800):
        """
        Extends the lock TTL, typically used when checkout begins.
        """
        try:
            r = SlotLockService.get_redis_client()
            key = SlotLockService._generate_key(employee_id, service_id, facility_id, start_time, end_time)
            # Only extend if the lock still exists
            if r.exists(key):
                r.expire(key, new_ttl_seconds)
                return True
            return False
        except Exception as e:
            logger.error(f"Error extending slot lock in Redis: {e}")
            return False

    @staticmethod
    def release_slot(employee_id, service_id, facility_id, start_time, end_time):
        """Manually release a slot lock."""
        try:
            r = SlotLockService.get_redis_client()
            key = SlotLockService._generate_key(employee_id, service_id, facility_id, start_time, end_time)
            r.delete(key)
        except Exception as e:
            logger.error(f"Error releasing slot lock in Redis: {e}")

    @staticmethod
    def is_locked(employee_id, service_id, facility_id, start_time, end_time):
        """Check if a slot is currently locked."""
        try:
            r = SlotLockService.get_redis_client()
            key = SlotLockService._generate_key(employee_id, service_id, facility_id, start_time, end_time)
            return r.exists(key)
        except Exception as e:
            logger.error(f"Error checking slot lock in Redis: {e}")
            return False
