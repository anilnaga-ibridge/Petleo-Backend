
import requests
import json

AUTH_URL = "http://127.0.0.1:8000/auth/api/auth/register/"

def test_auth_register():
    print(f"Testing Auth Register at {AUTH_URL}...")
    
    payload = {
        "full_name": "Test Employee",
        "email": "test_employee_debug@gmail.com",
        "phone_number": "9999999999",
        "role": "employee",
        "password": "password123" # Usually required for register?
    }
    
    try:
        # Note: EmployeeViewSet sends Authorization header, maybe we need it?
        # But register usually doesn't need auth? 
        # Let's check if EmployeeViewSet sends auth. Yes it does.
        # But wait, register endpoint usually creates a new user.
        # If it's an authenticated call, maybe it's a different endpoint?
        # The code says: auth_url = "http://localhost:8003/api/auth/register/"
        
        response = requests.post(AUTH_URL, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_auth_register()
