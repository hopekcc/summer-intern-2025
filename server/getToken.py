import os
from dotenv import load_dotenv
load_dotenv()
import requests

# 🔑 Your Firebase project Web API key (from Firebase Console)
API_KEY = os.getenv("FIREBASE_API_KEY")

# 👤 Test user credentials (must already exist in Firebase Auth)
EMAIL = "your_test_email@example.com"
PASSWORD = "your_test_password"

# 🔐 Firebase Auth REST API endpoint
url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"

payload = {
    "email": EMAIL,
    "password": PASSWORD,
    "returnSecureToken": True
}

# 📨 Make the request
response = requests.post(url, json=payload)

# 📋 Print results
if response.status_code == 200:
    id_token = response.json()["idToken"]
    print("✅ Firebase ID Token:")
    print(id_token)
else:
    print("❌ Login failed:", response.json())
