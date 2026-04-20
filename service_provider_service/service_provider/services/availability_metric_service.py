import logging
from django.utils import timezone
from ..models import AvailabilityMetric

logger = logging.getLogger(__name__)

class AvailabilityMetricService:
    @staticmethod
    def log_event(org_id, event_type, booking_id=None, staff_id=None, processing_time_ms=0):
        """
        Record availability performance events (Rule 7)
        event_type: CONVERTED, SLA_MISS, EXPIRED, DEMAND_LOSS
        """
        try:
            return AvailabilityMetric.objects.create(
                organization_id=org_id,
                event_type=event_type,
                booking_id=booking_id,
                assigned_staff_id=staff_id,
                processing_time_ms=processing_time_ms,
                metadata={
                    "logged_at": timezone.now().isoformat(),
                    "source": "automated_engine"
                }
            )
        except Exception as e:
            logger.error(f"Failed to log availability metric: {e}")
            return None
