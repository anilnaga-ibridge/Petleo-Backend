import requests

def test_sa_api(target):
    url = f"http://127.0.0.1:8003/api/superadmin/definitions/public/?target={target}"
    try:
        resp = requests.get(url)
        print(f"Target: {target}, Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Count: {len(data)}")
            for field in data:
                print(f" - {field['name']} ({field['field_type']})")
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")

print("Testing 'individual'...")
test_sa_api("individual")

print("\nTesting 'organization'...")
test_sa_api("organization")
