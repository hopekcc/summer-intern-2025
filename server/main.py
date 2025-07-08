from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED

import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.auth import InvalidIdTokenError

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cred = credentials.Certificate("firebase-service-account.json")
firebase_admin.initialize_app(cred)

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
        return decoded_token
    except InvalidIdTokenError as e:
        if "expired" in str(e).lower():
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token has expired")
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid ID token")
    except Exception as e:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=f"Token verification failed: {str(e)}")

@app.get("/")
def root():
    return {"message": "✅ FastAPI server is online. No authentication needed."}

@app.get("/protected")
def protected_route(user_data=Depends(verify_firebase_token)):
    return {
        "message": "🔒 Access granted to protected route!",
        "user": {
            "uid": user_data.get("uid"),
            "email": user_data.get("email")
        }
    }
