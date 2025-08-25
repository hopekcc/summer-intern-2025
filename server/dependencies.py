from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED
from firebase_admin import auth
from firebase_admin.auth import InvalidIdTokenError
import os

from server.scripts.utils import ConnectionManager

# Shared security object
security = HTTPBearer()

# Shared WebSocket connection manager
manager = ConnectionManager()

# --- Path Dependencies ---

# Base directory for path calculations
_base_dir = os.path.dirname(os.path.abspath(__file__))

def get_database_dir() -> str:
    """Returns the absolute path to the song database directory."""
    return os.path.join(_base_dir, "song_database")

def get_songs_dir(database_dir: str = Depends(get_database_dir)) -> str:
    """Returns the absolute path to the songs directory inside the database."""
    return os.path.join(database_dir, "songs")

def get_metadata_path(database_dir: str = Depends(get_database_dir)) -> str:
    """Returns the absolute path to the songs_metadata.json file."""
    return os.path.join(database_dir, "songs_metadata.json")

def get_songs_pdf_dir(database_dir: str = Depends(get_database_dir)) -> str:
    """Returns the absolute path to the songs_pdf directory."""
    return os.path.join(database_dir, "songs_pdf")


# Shared authentication dependency function
def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except InvalidIdTokenError as e:
        if "expired" in str(e).lower():
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token has expired")
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid ID token")
    except Exception as e:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=f"Token verification failed: {str(e)}") 