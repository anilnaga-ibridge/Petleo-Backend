from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Visit, VisitInvoice, InvoiceLineItem, FormSubmission, LabOrder, PharmacyDispense
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Visit)
def create_visit_invoice(sender, instance, created, **kwargs):
    if created:
        # Create Invoice
        invoice = VisitInvoice.objects.get_or_create(visit=instance)[0]
        
        # Add Base Consultation Fee
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

        if not invoice.items.filter(charge_type='CONSULTATION').exists():
            InvoiceLineItem.objects.create(
                invoice=invoice,
                charge_type='CONSULTATION',
                unit_price=fee_decimal,
                description=description
            )
            logger.info(f"✅ Created invoice and base charge for Visit {instance.id}")

@receiver(post_save, sender=LabOrder)
def handle_lab_order_billing(sender, instance, created, **kwargs):
    if created or instance.status == 'LAB_REQUESTED':
        visit = instance.visit
        invoice = getattr(visit, 'invoice', None)
        if not invoice:
            return
            
        # Check if this specific lab order is already billed
        if not invoice.items.filter(charge_type='LAB', reference_id=instance.id).exists():
            InvoiceLineItem.objects.create(
                invoice=invoice,
                charge_type='LAB',
                reference_id=instance.id,
                unit_price=instance.price_snapshot or 200.00,
                description=f"Lab Test: {instance.template.name}"
            )
            logger.info(f"✅ Added lab charge for Visit {visit.id}")

@receiver(post_save, sender=PharmacyDispense)
def handle_pharmacy_dispense_billing(sender, instance, created, **kwargs):
    if created:
        visit = instance.visit
        invoice = getattr(visit, 'invoice', None)
        if not invoice:
            return
            
        # Add medication charge
        # Logic: We can fetch price from linked prescription or medicine
        # For simplicity per spec, we'll use a snapshot or default
        InvoiceLineItem.objects.create(
            invoice=invoice,
            charge_type='MEDICINE',
            reference_id=instance.id,
            unit_price=300.00, # Placeholder or from Medicine
            description='Medication Dispensed'
        )
        logger.info(f"✅ Added pharmacy charge for Visit {visit.id}")
