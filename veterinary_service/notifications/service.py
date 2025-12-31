import logging

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def handle_event(event_type, payload):
        """
        Decides which notification to send based on event type.
        """
        logger.info(f"NotificationService received event: {event_type}")
        
        if event_type == 'LAB_RESULTS_READY':
            NotificationService.send_sms(payload.get('owner_id'), "Your pet's lab results are ready.")
            NotificationService.send_email(payload.get('owner_id'), "Lab Results Ready", "Please log in to view results.")
            
        elif event_type == 'PRESCRIPTION_FINALIZED':
             NotificationService.send_push(payload.get('owner_id'), "New prescription available.")
             
        elif event_type == 'VISIT_COMPLETED':
            NotificationService.send_email(payload.get('owner_id'), "Visit Summary", "Thank you for visiting.")

    @staticmethod
    def send_sms(user_id, message):
        logger.info(f"[STUB] Sending SMS to User {user_id}: {message}")

    @staticmethod
    def send_email(user_id, subject, body):
        logger.info(f"[STUB] Sending Email to User {user_id}: Subject: {subject}")

    @staticmethod
    def send_push(user_id, message):
        logger.info(f"[STUB] Sending Push Notification to User {user_id}: {message}")
