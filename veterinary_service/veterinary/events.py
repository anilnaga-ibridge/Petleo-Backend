from .kafka.producer import producer
import logging

logger = logging.getLogger(__name__)

# Event Types
VISIT_STATUS_CHANGED = 'VISIT_STATUS_CHANGED'
VISIT_SLA_BREACHED = 'VISIT_SLA_BREACHED'
LAB_RESULTS_READY = 'LAB_RESULTS_READY'
PRESCRIPTION_FINALIZED = 'PRESCRIPTION_FINALIZED'
MEDICINE_REMINDER_DUE = 'MEDICINE_REMINDER_DUE'
VISIT_COMPLETED = 'VISIT_COMPLETED'

def emit_domain_event(event_type, visit, extra_data=None):
    """
    Helper to emit standardized domain events.
    """
    payload = {
        "visit_id": str(visit.id),
        "clinic_id": str(visit.clinic.id),
        "pet_id": str(visit.pet.id),
        "pet_name": visit.pet.name,
        "owner_id": str(visit.pet.owner.id),
        "status": visit.status,
    }
    
    if extra_data:
        payload.update(extra_data)
        
    logger.info(f"Emitting Domain Event: {event_type} for Visit {visit.id}")
    producer.send_event(event_type, payload)
