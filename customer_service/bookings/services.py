import json
import logging
import redis
from .models import BookingItem
from django.conf import settings

logger = logging.getLogger(__name__)

class CapacityService:
    @staticmethod
    def get_facility_capacity(provider_id, facility_id):
        """
        Placeholder for fetching capacity from service_provider_service.
        In production, this would be a cached Kafka value or API call.
        """
        # Defaulting to 1 for now if unknown
        return 1 

    @staticmethod
    def check_availability(provider_id, facility_id, selected_time):
        """
        Checks if a slot is available based on capacity.
        """
        capacity = CapacityService.get_facility_capacity(provider_id, facility_id)
        
        # Count confirmed/pending bookings for this slot
        existing_count = BookingItem.objects.filter(
            provider_id=provider_id,
            facility_id=facility_id,
            selected_time=selected_time,
            status__in=['PENDING', 'CONFIRMED']
        ).count()
        
        return existing_count < capacity

class AutoAssignmentService:
    @staticmethod
    def assign_employee(provider_id, facility_id, selected_time):
        """
        Calls service_provider_service to find an available employee.
        """
        try:
            url = f"http://localhost:8002/api/provider/availability/{provider_id}/assign-employee/"
            payload = {
                "selected_time": selected_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(selected_time, 'strftime') else selected_time,
                "facility_id": str(facility_id)
            }
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                return response.json().get('employee_id')
        except Exception as e:
            logger.error(f"Auto-assignment failed for provider {provider_id}: {e}")
        
        return None

class SlotLockService:
    """
    Temporary slot reservation service using Redis.
    Shared across services via same Redis instance.
    """
    LOCK_TTL_SECONDS = 300  # 5 minutes

    @staticmethod
    def get_redis_client():
        url = getattr(settings, 'REDIS_URL', 'redis://127.0.0.1:6379/1')
        return redis.Redis.from_url(url)

    @staticmethod
    def _generate_key(employee_id, service_id, facility_id, start_time, end_time):
        """Identifier based on granular details to prevent conflicts across services."""
        start_str = start_time.isoformat() if hasattr(start_time, 'isoformat') else str(start_time)
        end_str = end_time.isoformat() if hasattr(end_time, 'isoformat') else str(end_time)
        return f"lock:slot:{employee_id}:{service_id}:{facility_id}:{start_str}:{end_str}"

    @staticmethod
    def lock_slot(employee_id, service_id, facility_id, start_time, end_time):
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
            if r.exists(key):
                r.expire(key, new_ttl_seconds)
                return True
            return False
        except Exception as e:
            logger.error(f"Error extending slot lock in Redis: {e}")
            return False

    @staticmethod
    def release_slot(employee_id, service_id, facility_id, start_time, end_time):
        try:
            r = SlotLockService.get_redis_client()
            key = SlotLockService._generate_key(employee_id, service_id, facility_id, start_time, end_time)
            r.delete(key)
        except Exception as e:
            logger.error(f"Error releasing slot lock in Redis: {e}")

    @staticmethod
    def lock_multiple(locks):
        """
        Attempts to acquire multiple locks at once. 
        'locks' is a list of tuples: (employee_id, service_id, facility_id, start_time, end_time).
        If ANY lock fails, releases all previously acquired locks in the list.
        """
        acquired_keys = []
        r = SlotLockService.get_redis_client()
        
        try:
            for emp_id, svc_id, fac_id, start_dt, end_dt in locks:
                key = SlotLockService._generate_key(emp_id, svc_id, fac_id, start_dt, end_dt)
                success = r.set(
                    key,
                    "locked",
                    nx=True,
                    ex=SlotLockService.LOCK_TTL_SECONDS
                )
                if success:
                    acquired_keys.append(key)
                else:
                    # Atomic Failure: Rollback all acquired locks
                    if acquired_keys:
                        r.delete(*acquired_keys)
                    return False
            return True
        except Exception as e:
            logger.error(f"Multi-lock failure: {e}")
            if acquired_keys:
                r.delete(*acquired_keys)
            return False

    @staticmethod
    def release_multiple(locks):
        """Releases multiple locks."""
        keys = [SlotLockService._generate_key(emp_id, svc_id, fac_id, start_dt, end_dt) for emp_id, svc_id, fac_id, start_dt, end_dt in locks]
        try:
            r = SlotLockService.get_redis_client()
            if keys:
                r.delete(*keys)
        except Exception as e:
            logger.error(f"Error releasing multiple locks: {e}")

class AvailabilityCacheService:
    @staticmethod
    def invalidate_slots(employee_id, facility_id, target_date):
        """
        Invalidate cache for a specific employee, facility, and date.
        Shared across services via same Redis instance.
        """
        date_str = target_date.isoformat() if hasattr(target_date, 'isoformat') else str(target_date)
        key = f"slots:{employee_id}:{facility_id}:{date_str}"
        from django.core.cache import cache
        cache.delete(key)

    @staticmethod
    def invalidate_employee_day(employee_id, target_date):
        """
        Invalidate ALL services for an employee on a specific date.
        """
        date_str = target_date.isoformat() if hasattr(target_date, 'isoformat') else str(target_date)
        pattern = f"slots:{employee_id}:*:{date_str}"
        from django.core.cache import cache
        try:
            if hasattr(cache, 'client') and hasattr(cache.client, 'get_client'):
                client = cache.client.get_client()
                for key in client.scan_iter(pattern):
                    client.delete(key)
        except Exception as e:
            logger.error(f"Cache pattern invalidation failed: {e}")
