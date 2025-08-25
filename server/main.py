import sys
import os

# This is the fix: Add the project root to the Python path
# This allows the imports to work correctly when running from the 'server' directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# FastAPI server for real-time song sharing with WebSocket support
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.auth import InvalidIdTokenError
import json
from dotenv import load_dotenv

from server.scripts.logger import logger
from server.scripts.database_models import init_database
from server.routers import songs, rooms
from server.dependencies import verify_firebase_token # Import for protected_route

# Load environment variables
load_dotenv()
FIREBASE_JSON = os.getenv("FIREBASE_JSON")

# Initialize FastAPI app
app = FastAPI()

# Initialize Firebase and database
if FIREBASE_JSON:
    service_account_info = json.loads(FIREBASE_JSON)
    cred = credentials.Certificate(service_account_info)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
else:
    raise ValueError("FIREBASE_JSON environment variable must be set")

init_database()

# TODO: SECURITY - This CORS policy is for development only.
# Restrict `allow_origins` to the frontend domain before production.
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    ip = request.headers.get("X-Forwarded-For", request.client.host)
    method = request.method
    url = str(request.url)
    user_agent = request.headers.get("user-agent", "unknown")
    
    uid = email = "-"
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split()[1]
        try:
            decoded = auth.verify_id_token(token)
            uid = decoded.get("uid", "-")
            email = decoded.get("email", "-")
        except InvalidIdTokenError:
            logger.warning(f"Invalid token attempt from IP: {ip}")
        except Exception:
            logger.warning("Error decoding token", exc_info=True)
    
    try:
        response = await call_next(request)
        logger.info(f"{method} {url} - {response.status_code} | IP: {ip} | UID: {uid} | Email: {email} | UA: {user_agent}")
        return response
    except Exception:
        logger.error(f"Unhandled error in {method} {url} | IP: {ip} | UID: {uid} | Email: {email}", exc_info=True)
        raise

# ============================================================================
# BASIC ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    return {"message": "FastAPI server is online. No authentication needed."}

@app.get("/protected")
def protected_route(user_data=Depends(verify_firebase_token)):
    return {
        "message": "Access granted to protected route!",
        "user": {
            "uid": user_data.get("uid"),
            "email": user_data.get("email")
        }
    }

# Include routers
app.include_router(songs.router, prefix="/songs", tags=["songs"])
app.include_router(rooms.router, prefix="/rooms", tags=["rooms"])


