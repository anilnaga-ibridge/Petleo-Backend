import requests
import logging
from django.conf import settings

logger = logging.getLogger('veterinary.auth')

class AuthIntegrationService:
    """
    Handles communication with the Auth Service for User/Owner management.
    """
    # Assuming Auth Service is on port 8000
    AUTH_SERVICE_URL = "http://127.0.0.1:8000"

    @staticmethod
    def fetch_user_by_phone(phone_number):
        """Fetch user basic info from Auth Service by phone number."""
        try:
            url = f"{AuthIntegrationService.AUTH_SERVICE_URL}/api/auth/internal/user-by-phone/"
            response = requests.get(url, params={"phone_number": phone_number}, timeout=5)
            if response.status_code == 200:
                data = response.json()
                # Ensure we return a consistent format
                return {
                    'auth_user_id': data.get('auth_user_id'),
                    'full_name': data.get('full_name'),
                    'email': data.get('email')
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching user by phone from Auth Service: {e}")
            return None

    @staticmethod
    def verify_user_exists(auth_user_id=None, phone_number=None):
        """
        Verify if a user still exists in the Auth Service.
        Tries by auth_user_id first, then falls back to phone_number.
        Returns user data dict if found, None if not found.
        """
        try:
            if phone_number:
                url = f"{AuthIntegrationService.AUTH_SERVICE_URL}/api/auth/internal/user-by-phone/"
                resp = requests.get(url, params={"phone_number": phone_number}, timeout=5)
                if resp.status_code == 200:
                    return resp.json()
            return None
        except Exception as e:
            logger.error(f"Error verifying user existence in Auth Service: {e}")
            # Return True to avoid accidentally deleting records if Auth Service is down
            return True

    @staticmethod
    def register_customer(full_name, phone_number, email=None):
        """
        Registers a new customer in the Auth Service.
        If already exists, fetches and returns their auth_user_id.
        """
        url = f"{AuthIntegrationService.AUTH_SERVICE_URL}/api/auth/register/"
        payload = {
            "full_name": full_name,
            "phone_number": phone_number,
            "email": email,
            "role": "customer"
        }
        
        try:
            logger.info(f"Registering user in Auth Service: {phone_number}")
            response = requests.post(url, json=payload, timeout=5)
            
            if response.status_code == 201:
                data = response.json()
                auth_user_id = data.get('auth_user_id') or data.get('id')
                logger.info(f"Successfully registered user {phone_number} with Auth ID {auth_user_id}")
                return auth_user_id
            elif response.status_code == 400:
                # Likely already registered, try fetching
                logger.info(f"Registration returned 400 for {phone_number}. Attempting fetch.")
                user_data = AuthIntegrationService.fetch_user_by_phone(phone_number)
                if user_data:
                    return user_data.get("auth_user_id")
                return None
            else:
                logger.error(f"Failed to register user in Auth Service: {response.text}")
                return None
        except Exception as e:
            logger.exception(f"Error calling Auth Service: {e}")
            return None

    @staticmethod
    def update_customer(auth_user_id, data):
        """
        Updates an existing user in the Auth Service.
        """
        url = f"{AuthIntegrationService.AUTH_SERVICE_URL}/users/{auth_user_id}/"
        
        # Map fields to match Auth Service User schema
        payload = {}
        if 'name' in data: payload['full_name'] = data['name']
        if 'full_name' in data: payload['full_name'] = data['full_name']
        if 'email' in data: payload['email'] = data['email']
        if 'phone' in data: payload['phone_number'] = data['phone']
        if 'phone_number' in data: payload['phone_number'] = data['phone_number']
        
        if not payload:
            return True

        try:
            logger.info(f"Updating user {auth_user_id} in Auth Service")
            response = requests.patch(url, json=payload, timeout=5)
            
            if response.status_code in [200, 204]:
                logger.info(f"Successfully updated user {auth_user_id} in Auth Service")
                return True
            else:
                logger.error(f"Failed to update user in Auth Service: {response.text}")
                return False
        except Exception as e:
            logger.exception(f"Error calling Auth Service: {e}")
            return False
