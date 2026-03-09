from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Visit, VisitInvoice, InvoiceLineItem, FormSubmission, DynamicFieldDefinition
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Visit)
def create_visit_invoice(sender, instance, created, **kwargs):
    if created:
        # Create Invoice
        invoice = VisitInvoice.objects.create(visit=instance)
        
        # Add Base Consultation Fee
        # Logic: Pull from linked appointment snapshot, fallback to default
        fee = 500.00
        description = 'Base Consultation Fee'
        
        if instance.appointment:
            fee = instance.appointment.consultation_fee
            if instance.appointment.consultation_type:
                description = f"Consultation: {instance.appointment.consultation_type}"
        
        from decimal import Decimal
        
        try:
            fee_decimal = Decimal(str(fee))
        except:
            fee_decimal = Decimal('0.00')

        InvoiceLineItem.objects.create(
            invoice=invoice,
            charge_type='CONSULTATION',
            unit_price=fee_decimal,
            description=description
        )
        logger.info(f"✅ Created invoice and base charge for Visit {instance.id}")

@receiver(post_save, sender=Visit)
def handle_visit_status_change(sender, instance, **kwargs):
    # We can use status changes to trigger charges if not already handled
    # For example, if status changes to LAB_ORDERED
    if instance.status == 'LAB_ORDERED':
        # Check if lab charge already exists for this visit
        invoice = getattr(instance, 'invoice', None)
        if invoice:
            if not invoice.items.filter(charge_type='LAB').exists():
                # Add a placeholder lab charge or fetch from pricing
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    charge_type='LAB',
                    unit_price=200.00, # Placeholder
                    description='Lab Test Fee'
                )
                logger.info(f"✅ Added lab charge for Visit {instance.id}")

@receiver(post_save, sender=FormSubmission)
def handle_form_submission_billing(sender, instance, created, **kwargs):
    if created:
        visit = instance.visit
        invoice = getattr(visit, 'invoice', None)
        if not invoice:
            return

        # If it's a prescription form
        if instance.form_definition.code == 'PRESCRIPTION':
            # Add medicine charges based on data
            # This is a simplified example
            InvoiceLineItem.objects.create(
                invoice=invoice,
                charge_type='MEDICINE',
                reference_id=instance.id,
                unit_price=300.00, # Placeholder
                description='Prescription Medicines'
            )
            logger.info(f"✅ Added medicine charge for Visit {visit.id}")
