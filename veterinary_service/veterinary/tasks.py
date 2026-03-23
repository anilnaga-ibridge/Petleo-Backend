from celery import shared_task
from django.utils import timezone
from .models import MedicineReminderSchedule
import logging

logger = logging.getLogger(__name__)

@shared_task
def check_due_medicine_reminders():
    """
    Periodic task to check for due medicine reminders and send notifications.
    Suggested frequency: Every 15 minutes.
    """
    now = timezone.now()
    window_start = now
    window_end = now + timezone.timedelta(minutes=15)
    
    # Fetch pending schedules due in the next 15 minutes
    due_doses = MedicineReminderSchedule.objects.filter(
        status='PENDING',
        scheduled_datetime__range=(window_start, window_end)
    ).select_related('reminder', 'reminder__pet', 'reminder__medicine')
    
    for dose in due_doses:
        # Logistic: Send Push/Email Notification to Owner
        # For now, we log it.
        owner_id = dose.reminder.pet_owner_auth_id
        pet_name = dose.reminder.pet.name
        med_name = dose.reminder.medicine.name
        
        logger.info(f"🔔 REMINDER: Sending notification to Pet Owner {owner_id} for {pet_name}'s {med_name} dose.")
        
        # Integration with notification service would go here
        # send_pet_owner_notification(owner_id, "Medicine Due", f"It's time for {pet_name}'s {med_name}!")
        
        # We don't mark as TAKEN here, the user does that from the app.
    
    return f"Processed {due_doses.count()} due reminders."


@shared_task
def process_vaccination_deworming_reminders():
    """
    Run every 5 minutes.
    Checks vaccination_reminders and deworming_reminders:
    status = PENDING
    reminder_date <= current_date
    Sends WhatsApp message and updates status = SENT.
    """
    from datetime import date
    from .models import SystemVaccinationReminder, SystemDewormingReminder

    today = date.today()
    
    # 1. Vaccination Reminders
    pending_vaccines = SystemVaccinationReminder.objects.filter(
        status='PENDING',
        reminder_date__lte=today
    ).select_related('pet', 'pet__owner')

    for rem in pending_vaccines:
        pet_name = rem.pet.name
        owner_name = rem.pet.owner.name if rem.pet.owner else "Pet Owner"
        vaccine_name = rem.vaccine_name
        next_due_date = rem.next_due_date.strftime("%Y-%m-%d")

        message = (
            f"Hello {owner_name},\n\n"
            f"Your pet {pet_name} is due for vaccination.\n\n"
            f"Vaccine: {vaccine_name}\n"
            f"Due Date: {next_due_date}\n\n"
            f"Please visit the clinic.\n\nThank you."
        )
        
        logger.info(f"📱 WhatsApp (Vaccination) -> {owner_name}: {message.replace(chr(10), ' ')}")
        
        # Mark SENT
        rem.status = 'SENT'
        rem.save(update_fields=['status'])


    # 2. Deworming Reminders
    pending_deworming = SystemDewormingReminder.objects.filter(
        status='PENDING',
        reminder_date__lte=today
    ).select_related('pet', 'pet__owner')

    for rem in pending_deworming:
        pet_name = rem.pet.name
        owner_name = rem.pet.owner.name if rem.pet.owner else "Pet Owner"
        medicine_name = rem.medicine_name
        next_due_date = rem.next_due_date.strftime("%Y-%m-%d")

        message = (
            f"Hello {owner_name},\n\n"
            f"Your pet {pet_name} is due for deworming.\n\n"
            f"Medicine: {medicine_name}\n"
            f"Due Date: {next_due_date}\n\n"
            f"Please visit the clinic.\n\nThank you."
        )
        
        logger.info(f"📱 WhatsApp (Deworming) -> {owner_name}: {message.replace(chr(10), ' ')}")
        
        # Mark SENT
        rem.status = 'SENT'
        rem.save(update_fields=['status'])

    return f"Processed {pending_vaccines.count()} vaccination and {pending_deworming.count()} deworming reminders."
