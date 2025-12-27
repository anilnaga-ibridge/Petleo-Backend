import requests
import time
import uuid

BASE_URL = "http://localhost:8001/api/v1/auth"  # Assuming Auth Service runs on 8001

def test_registration():
    # Generate unique user data
    unique_id = uuid.uuid4().hex[:8]
    phone = f"99{unique_id[:8]}" # Ensure 10 digits
    email = f"test_{unique_id}@example.com"
    
    payload = {
        "phone_number": phone,
        "email": email,
        "full_name": f"Test User {unique_id}",
        "role": "individual",
        "password": "password123"
    }

    print(f"--- Test 1: New Registration ({email}) ---")
    start_time = time.time()
    try:
        response = requests.post(f"{BASE_URL}/register/", json=payload)
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {duration:.2f} seconds")
        print(f"Response: {response.text}")
        
        if response.status_code == 201:
            print("✅ Registration Successful")
        else:
            print("❌ Registration Failed")
            
    except Exception as e:
        print(f"❌ Request Failed: {e}")

    print("\n--- Test 2: Duplicate Registration (Same Email & Phone) ---")
    try:
        response = requests.post(f"{BASE_URL}/register/", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        expected_msg = "thank for registration to your site ,your using phone number and email is alredy in use please register using aothere mail or phone numebr ,what is alredy exist"
        if expected_msg in response.text:
             print("✅ Correct Error Message Received")
        else:
             print(f"❌ Incorrect Error Message. Expected: '{expected_msg}'")

    except Exception as e:
        print(f"❌ Request Failed: {e}")

if __name__ == "__main__":
    test_registration()
