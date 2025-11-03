import logging
from django.core.mail import send_mail, get_connection
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

def send_password_email(user_email, username, password, sender_email=None, sender_password=None):
    """
    Send generated password to user's email using dynamic sender credentials
    
    Args:
        user_email: Recipient email address
        username: Username for the new account
        password: Generated password
        sender_email: Email to send from (if None, uses settings)
        sender_password: Password for sender email (if None, uses settings)
    """
    try:
        subject = 'Your Account Password - Authentication Service'
        
        # Create HTML email content
        html_message = f"""
        <html>
        <body>
            <h2>Welcome to the Authentication Service!</h2>
            <p>Dear {username},</p>
            <p>Your account has been successfully created. Here are your login credentials:</p>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Username:</strong> {username}</p>
                <p><strong>Email:</strong> {user_email}</p>
                <p><strong>Password:</strong> <code style="background-color: #e8e8e8; padding: 2px 5px; border-radius: 3px;">{password}</code></p>
            </div>
            <p><strong>Important Security Notes:</strong></p>
            <ul>
                <li>Please change your password after your first login</li>
                <li>Keep your credentials secure and do not share them</li>
                <li>This password was automatically generated for security</li>
            </ul>
            <p>If you did not request this account, please contact our support team immediately.</p>
            <br>
            <p>Best regards,<br>Authentication Service Team</p>
        </body>
        </html>
        """
        
        # Create plain text version
        plain_message = f"""
        Welcome to the Authentication Service!
        
        Dear {username},
        
        Your account has been successfully created. Here are your login credentials:
        
        Username: {username}
        Email: {user_email}
        Password: {password}
        
        Important Security Notes:
        - Please change your password after your first login
        - Keep your credentials secure and do not share them
        - This password was automatically generated for security
        
        If you did not request this account, please contact our support team immediately.
        
        Best regards,
        Authentication Service Team
        """
        
        # Use dynamic sender credentials if provided and not using console backend
        if sender_email and sender_password and not settings.EMAIL_BACKEND.endswith('console.EmailBackend'):
            # Create custom email connection with dynamic credentials
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=sender_email,
                password=sender_password,
                use_tls=settings.EMAIL_USE_TLS,
            )
            from_email = sender_email
        else:
            # Use default connection and settings (works with console backend)
            connection = None
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=from_email,
            recipient_list=[user_email],
            fail_silently=False,
            connection=connection,
        )
        
        logger.info(f"Password email sent successfully to {user_email} from {from_email}")
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "535" in error_msg and "Username and Password not accepted" in error_msg:
            logger.error(f"Email authentication failed for {sender_email or 'default'}. Please check:")
            logger.error("1. Use correct email credentials")
            logger.error("2. For Gmail: Enable 2-Factor Authentication and use App Password")
            logger.error("3. Verify email and password are correct in request")
        else:
            logger.error(f"Failed to send password email to {user_email}: {error_msg}")
        return False

def send_password_reset_email(user_email, username, new_password):
    """
    Send new password after reset to user's email
    """
    try:
        subject = 'Password Reset - Authentication Service'
        
        html_message = f"""
        <html>
        <body>
            <h2>Password Reset Confirmation</h2>
            <p>Dear {username},</p>
            <p>Your password has been successfully reset. Here is your new password:</p>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>New Password:</strong> <code style="background-color: #e8e8e8; padding: 2px 5px; border-radius: 3px;">{new_password}</code></p>
            </div>
            <p><strong>Security Reminder:</strong></p>
            <ul>
                <li>Please change this password after logging in</li>
                <li>Use a strong, unique password</li>
                <li>Do not share your credentials with anyone</li>
            </ul>
            <p>If you did not request this password reset, please contact our support team immediately.</p>
            <br>
            <p>Best regards,<br>Authentication Service Team</p>
        </body>
        </html>
        """
        
        plain_message = f"""
        Password Reset Confirmation
        
        Dear {username},
        
        Your password has been successfully reset. Here is your new password:
        
        New Password: {new_password}
        
        Security Reminder:
        - Please change this password after logging in
        - Use a strong, unique password
        - Do not share your credentials with anyone
        
        If you did not request this password reset, please contact our support team immediately.
        
        Best regards,
        Authentication Service Team
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
        
        logger.info(f"Password reset email sent successfully to {user_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user_email}: {str(e)}")
        return False