
import requests
import uuid

BASE_URL = "http://localhost:8001/api/provider"

# Helper to get tokens or simulate auth if needed
# In this environment, we usually have a test provider
provider_id = "6f5165ab-f077-46ac-ba32-6a09ef13baef" # Example from context if available

def test_public_profile():
    print(f"Testing Public Profile for {provider_id}...")
    url = f"{BASE_URL}/public-profile/{provider_id}/"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.data()
        print("✅ Public Profile fetched successfully")
        print(f"Provider Name: {data.get('providerName')}")
        print(f"Has Menu: {len(data.get('menu', [])) > 0}")
        print(f"Has Detailed Profile: {data.get('detailed_profile') is not None}")
    else:
        print(f"❌ Failed to fetch public profile: {res.status_code}")
        print(res.text)

if __name__ == "__main__":
    test_public_profile()
