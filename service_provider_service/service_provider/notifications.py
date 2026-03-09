import logging
from .models import ServiceProvider, OrganizationEmployee, VerifiedUser

logger = logging.getLogger("notifications")

def handle_booking_created_notification(event_data):
    """
    Handles the BOOKING_CREATED event by notifying the provider and employee.
    """
    booking_id = event_data.get("booking_id")
    provider_auth_id = event_data.get("provider_auth_id")
    assigned_employee_id = event_data.get("assigned_employee_id")
    owner_name = event_data.get("owner_name", "A pet owner")
    pet_name = event_data.get("pet_name", "their pet")
    service_name = event_data.get("service_name", "a service")
    selected_time = event_data.get("selected_time")

    logger.info(f"🔔 Processing notifications for booking {booking_id}")

    # 1. Notify Provider (Organization/Clinic)
    try:
        provider = ServiceProvider.objects.get(verified_user__auth_user_id=provider_auth_id)
        provider_email = provider.verified_user.email
        provider_name = provider.verified_user.full_name
        
        message = (
            f"Hello {provider_name},\n\n"
            f"A new booking has been confirmed for your clinic!\n"
            f"Customer: {owner_name}\n"
            f"Pet: {pet_name}\n"
            f"Service: {service_name}\n"
            f"Time: {selected_time}\n\n"
            f"Please check your dashboard for details."
        )
        # Simulation: In a real system, call an Email/SMS gateway here
        send_simulated_alert(provider_email, "New Booking Confirmed", message, "PROVIDER")
        
    except ServiceProvider.DoesNotExist:
        logger.warning(f"⚠️ Provider {provider_auth_id} not found for notification.")

    # 2. Notify Assigned Employee (Doctor/Staff)
    if assigned_employee_id:
        try:
            employee = OrganizationEmployee.objects.get(auth_user_id=assigned_employee_id)
            employee_email = employee.email
            employee_name = employee.full_name
            
            message = (
                f"Hello {employee_name},\n\n"
                f"You have been assigned a new appointment!\n"
                f"Customer: {owner_name}\n"
                f"Pet: {pet_name}\n"
                f"Service: {service_name}\n"
                f"Time: {selected_time}\n\n"
                f"See you there!"
            )
            # Simulation: Call Email/SMS gateway
            send_simulated_alert(employee_email, "New Appointment Assigned", message, "EMPLOYEE")
            
        except OrganizationEmployee.DoesNotExist:
            # Fallback: Maybe it's an individual provider who acts as their own employee
            logger.info(f"ℹ️ Employee {assigned_employee_id} not found in OrganizationEmployee, checking VerifiedUser.")
            try:
                user = VerifiedUser.objects.get(auth_user_id=assigned_employee_id)
                send_simulated_alert(user.email, "New Appointment Alert", f"New booking for you at {selected_time}", "INDIVIDUAL_PRO")
            except VerifiedUser.DoesNotExist:
                logger.warning(f"⚠️ Employee {assigned_employee_id} not found for notification.")

def send_simulated_alert(recipient, subject, body, target_type):
    """
    Simulates sending an alert (Email/SMS/Push).
    """
    logger.info(f"\n{'='*60}\n[SIMULATED {target_type} ALERT]\nRecipient: {recipient}\nSubject: {subject}\n\n{body}\n{'='*60}\n")
