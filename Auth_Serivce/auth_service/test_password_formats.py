#!/usr/bin/env python3
"""
Test multiple password formats for Gmail SMTP
"""

import smtplib

def test_password_formats():
    print("🔧 TESTING DIFFERENT PASSWORD FORMATS")
    print("=" * 50)
    
    host = 'smtp.gmail.com'
    port = 587
    username = 'anil.naga@ibridge.digital'
    
    # Test different password formats
    passwords = [
        'mfyt rtlc duxn jkso'
    ]
    
    for i, password in enumerate(passwords, 1):
        print(f"\n🧪 Test {i}: Password format '{password}'")
        print(f"Length: {len(password)} characters")
        
        try:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
            server.login(username, password)
            print("✅ SUCCESS! This password format works!")
            server.quit()
            break
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ Failed: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    else:
        print("\n❌ None of the password formats worked.")
        print("\nPossible issues:")
        print("1. The app password might be expired or revoked")
        print("2. 2FA might not be properly enabled")
        print("3. The app password might be for a different email")
        print("4. There might be additional security settings blocking access")

if __name__ == "__main__":
    test_password_formats()