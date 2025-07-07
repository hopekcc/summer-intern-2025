from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED

import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.auth import InvalidIdTokenError

app = FastAPI()

# CORS settings (allow all origins for testing — restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow any frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔑 Initialize Firebase Admin using your downloaded private key
cred = credentials.Certificate("firebase-service-account.json")
firebase_admin.initialize_app(cred)

# 🔐 Token verification dependency
def verify_firebase_token(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header format")

    token = parts[1]
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token  # contains email, uid, etc.
    except InvalidIdTokenError as e:
        if "expired" in str(e).lower():
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token has expired")
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid ID token")
    except Exception as e:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=f"Token verification failed: {str(e)}")

# 🌐 Public route
@app.get("/")
def root():
    return {"message": "✅ FastAPI server is online. No authentication needed."}

# 🔐 Protected route
@app.get("/protected")
def protected_route(user_data=Depends(verify_firebase_token)):
    return {
        "message": "🔒 Access granted to protected route!",
        "user": {
            "uid": user_data.get("uid"),
            "email": user_data.get("email")
        }
    }
