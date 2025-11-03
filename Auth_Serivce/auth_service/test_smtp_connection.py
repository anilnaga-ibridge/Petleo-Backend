#!/usr/bin/env python3
"""
Simple SMTP connection test for Gmail
"""

import smtplib
import socket
from email.mime.text import MIMEText

def test_smtp_connection():
    print("🔧 TESTING GMAIL SMTP CONNECTION")
    print("=" * 50)
    
    host = 'smtp.gmail.com'
    port = 587
    username = 'anil.naga@ibridge.digital'
    password = 'mfyt rtlc duxn jkso'  # New app password
    
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    
    try:
        print("\n🔌 Step 1: Creating SMTP connection...")
        server = smtplib.SMTP(host, port, timeout=30)
        print("✅ Connection created successfully")
        
        print("\n🔐 Step 2: Starting TLS...")
        server.starttls()
        print("✅ TLS started successfully")
        
        print("\n🔑 Step 3: Logging in...")
        server.login(username, password)
        print("✅ Login successful!")
        
        print("\n📧 Step 4: Sending test email...")
        msg = MIMEText("Test email from Django microservice")
        msg['Subject'] = 'Django Email Test'
        msg['From'] = username
        msg['To'] = 'nagaanil0329@gmail.com'
        
        server.send_message(msg)
        print("✅ Email sent successfully!")
        
        server.quit()
        print("✅ Connection closed")
        
    except socket.timeout:
        print("❌ Connection timeout - check network/firewall")
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("   - Check if app password is correct")
        print("   - Verify 2FA is enabled")
        print("   - Make sure app password is for the correct email")
    except smtplib.SMTPException as e:
        print(f"❌ SMTP error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_smtp_connection()