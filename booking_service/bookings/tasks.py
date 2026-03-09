import logging
from django.utils import timezone
from datetime import timedelta
from .models import Booking, BookingItem, VisitGroup
from .services import AvailabilityCacheService

logger = logging.getLogger(__name__)

def expire_pending_bookings(timeout_minutes=15):
    """
    Finds PENDING bookings older than timeout and expires them.
    Freies up slots for others to book.
    """
    cutoff = timezone.now() - timedelta(minutes=timeout_minutes)
    
    # 1. Find Expired Booking Headers
    expired_bookings = Booking.objects.filter(
        status='PENDING',
        created_at__lt=cutoff
    )
    
    count = expired_bookings.count()
    if count == 0:
        return 0

    logger.info(f"Expiring {count} stale PENDING bookings.")

    for booking in expired_bookings:
        # Update Items and clear cache
        items = booking.items.all()
        for item in items:
            item.status = 'CANCELLED'
            item.rejection_reason = "Transaction timeout"
            item.save()
            
            # Atomic invalidation
            AvailabilityCacheService.invalidate_slots(
                item.assigned_employee_id,
                item.facility_id,
                item.selected_time.date()
            )
        
        booking.status = 'CANCELLED'
        booking.save()

    # 2. Cleanup VisitGroups if they are empty or all cancelled
    # (Optional: specialized logic for VisitGroup if needed)
    
    return count
