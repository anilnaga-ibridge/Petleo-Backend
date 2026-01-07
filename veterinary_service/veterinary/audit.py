from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Visit, FormSubmission, VeterinaryAuditLog, VisitInvoice
from .middleware import get_current_user_id
import logging

logger = logging.getLogger(__name__)

def log_medical_action(visit, action_type, capability=None, metadata=None):
    user_id = get_current_user_id() or "SYSTEM"
    VeterinaryAuditLog.objects.create(
        visit=visit,
        action_type=action_type,
        performed_by=user_id,
        capability_used=capability,
        metadata=metadata or {}
    )
    logger.info(f"📝 Audit Log: {action_type} for Visit {visit.id} by {user_id}")

@receiver(post_save, sender=Visit)
def audit_visit_changes(sender, instance, created, **kwargs):
    if created:
        log_medical_action(instance, 'VISIT_CREATED', capability='VETERINARY_VISITS')
    else:
        # Check for status change
        # Note: This is a simplified check. In a real app, you'd compare with old_instance.
        log_medical_action(
            instance, 
            'STATUS_CHANGE', 
            metadata={'new_status': instance.status}
        )

@receiver(post_save, sender=FormSubmission)
def audit_form_submissions(sender, instance, created, **kwargs):
    if created:
        action_type = 'OTHER'
        capability = None
        
        if instance.form_definition.code == 'VITALS_FORM':
            action_type = 'VITALS_ENTERED'
            capability = 'VETERINARY_VITALS'
        elif instance.form_definition.code == 'PRESCRIPTION_FORM':
            action_type = 'PRESCRIPTION_CREATED'
            capability = 'VETERINARY_PRESCRIPTIONS'
        elif instance.form_definition.code == 'LAB_FORM':
            action_type = 'LAB_ORDERED'
            capability = 'VETERINARY_LABS'
            
        log_medical_action(
            instance.visit, 
            action_type, 
            capability=capability,
            metadata={'form_id': str(instance.id)}
        )

@receiver(post_save, sender=VisitInvoice)
def audit_invoice_payment(sender, instance, **kwargs):
    if instance.status == 'PAID':
        log_medical_action(
            instance.visit, 
            'INVOICE_PAID', 
            capability='VETERINARY_BILLING',
            metadata={'invoice_id': str(instance.id), 'total': str(instance.total)}
        )
