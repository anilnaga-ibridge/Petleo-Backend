#!/usr/bin/env python3
"""
🧪 CONSOLE MODE TEST - Email Functionality Test

This script tests the registration with password generation in CONSOLE mode.
You should see the email content printed in your Django console.
"""

import requests
import json
import time

AUTH_SERVICE_URL = "http://127.0.0.1:8000/auth/register/"

def test_console_email():
    """Test registration without password in console mode"""
    
    print("🧪 Testing Registration with Password Generation (Console Mode)")
    print("=" * 60)
    
    # Test data - NO password field
    test_data = {
        "username": f"testuser_{int(time.time())}",  # Unique username
        "email": "testuser@example.com",
        "role": 2  # Use valid role ID (Admin)
        # No password = should generate one
    }
    
    print(f"📤 Sending request to: {AUTH_SERVICE_URL}")
    print(f"📋 Request data: {json.dumps(test_data, indent=2)}")
    print()
    
    try:
        response = requests.post(AUTH_SERVICE_URL, json=test_data)
        
        print("📊 RESPONSE:")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body:")
        response_data = response.json()
        print(json.dumps(response_data, indent=2))
        
        # Analysis
        if response.status_code == 201:
            password_info = response_data.get('password_info', {})
            if password_info.get('generated'):
                print("\n✅ SUCCESS: Password was generated!")
                if password_info.get('email_sent'):
                    print("✅ Email sent successfully!")
                    print("👀 Check your Django console for the email content!")
                else:
                    print("⚠️  Email sending failed, but password is in response:")
                    print(f"🔑 Generated Password: {password_info.get('generated_password')}")
            else:
                print("❌ Password was not generated - check the logic")
        else:
            print(f"❌ Registration failed with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to Django server")
        print("Make sure Django is running: python manage.py runserver 8000")
    except Exception as e:
        print(f"❌ ERROR: {e}")

def test_with_password():
    """Test registration WITH password (should not generate)"""
    
    print("\n🧪 Testing Registration with Provided Password")
    print("=" * 60)
    
    test_data = {
        "username": f"testuser_pwd_{int(time.time())}",
        "email": "testuser2@example.com",
        "password": "MyStrongPassword123!",  # Password provided
        "role": 2  # Use valid role ID (Admin)
    }
    
    print(f"📤 Sending request with password...")
    print(f"📋 Request data: {json.dumps(test_data, indent=2)}")
    print()
    
    try:
        response = requests.post(AUTH_SERVICE_URL, json=test_data)
        
        print("📊 RESPONSE:")
        print(f"Status Code: {response.status_code}")
        response_data = response.json()
        print(json.dumps(response_data, indent=2))
        
        if response.status_code == 201:
            password_info = response_data.get('password_info')
            if not password_info:
                print("✅ SUCCESS: No password generated (as expected)")
            else:
                print("⚠️  Unexpected: Password info present when password was provided")
        else:
            print(f"❌ Registration failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    print("🎯 EMAIL FUNCTIONALITY TEST SUITE")
    print("🔧 Current Mode: CONSOLE (emails printed to Django console)")
    print()
    
    # Test 1: No password (should generate and email)
    test_console_email()
    
    # Test 2: With password (should not generate)
    test_with_password()
    
    print("\n" + "=" * 60)
    print("✅ Tests completed!")
    print("📝 Check your Django console for email content if password was generated.")
    print("🔧 To enable real email sending:")
    print("   1. Get Gmail App Password")
    print("   2. Update .env file with real credentials") 
    print("   3. Switch EMAIL_BACKEND to smtp in settings.py")