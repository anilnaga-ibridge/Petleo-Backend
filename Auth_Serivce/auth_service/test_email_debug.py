#!/usr/bin/env python3
"""
Email debugging script to test Gmail SMTP configuration
"""

import os
import sys
import django
from django.core.mail import send_mail
from django.conf import settings

# Add the project directory to Python path
sys.path.append('d:/Anil/PythonPracties/microservice_archy/Auth_Serivce/auth_service')

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_service.settings')

# Setup Django
django.setup()

def test_email_sending():
    print("🔧 EMAIL CONFIGURATION TEST")
    print("=" * 50)
    
    # Print current email settings
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'Not set'}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    
    print("\n🧪 Testing email sending...")
    
    try:
        # Test sending an email
        result = send_mail(
            subject='Test Email from Django',
            message='This is a test email to verify SMTP configuration.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['nagaanil0329@gmail.com'],
            fail_silently=False,
        )
        
        if result:
            print("✅ Email sent successfully!")
            print(f"Number of emails sent: {result}")
        else:
            print("❌ Email sending failed - no emails sent")
            
    except Exception as e:
        print(f"❌ Email sending failed with error:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        
        # Print additional debug info for SMTP errors
        if hasattr(e, 'smtp_code'):
            print(f"SMTP Code: {e.smtp_code}")
        if hasattr(e, 'smtp_error'):
            print(f"SMTP Error: {e.smtp_error}")

if __name__ == "__main__":
    test_email_sending()