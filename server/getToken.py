
import requests

API_KEY = "AIzaSyBzgB6KsEmncRvh3bQTaPUp8Z2qWNCtRdM"

EMAIL = "your_test_email@example.com"
PASSWORD = "your_test_password"

url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"

payload = {
    "email": EMAIL,
    "password": PASSWORD,
    "returnSecureToken": True
}

response = requests.post(url, json=payload)

if response.status_code == 200:
    id_token = response.json()["idToken"]
    print("✅ Firebase ID Token:")
    print(id_token)
else:
    print("❌ Login failed:", response.json())
