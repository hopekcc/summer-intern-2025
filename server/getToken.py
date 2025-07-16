import os
import requests
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
API_KEY = os.getenv("FIREBASE_API_KEY")

# === Test user credentials (must be set in .env or hardcoded safely) ===
EMAIL = "your_test_email@example.com"
PASSWORD = "your_test_password"

if not API_KEY:
    print("❌ Missing FIREBASE_API_KEY in environment.")
    exit(1)

# === Firebase Auth endpoint ===
url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"

payload = {
    "email": EMAIL,
    "password": PASSWORD,
    "returnSecureToken": True
}

# === Make request ===
try:
    response = requests.post(url, json=payload)
    response.raise_for_status()
    id_token = response.json()["idToken"]
    print("✅ Firebase ID Token:")
    print(id_token)
except requests.exceptions.RequestException as e:
    print("❌ Login request failed:", e)
    if response.content:
        try:
            print(response.json())
        except Exception:
            print(response.content.decode())
