import requests
# Creating a dummy role using the API
url = "http://127.0.0.1:8002/api/provider/roles/"
# Let's see what happens if we just send a request without auth. It should be 401.
res = requests.post(url, json={"name": "Veterinary Doctor", "capabilities": []})
print(res.status_code, res.text)
