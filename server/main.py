from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED

import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.auth import InvalidIdTokenError

from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security

from logger import logger
from firebase_admin import auth
from firebase_admin._auth_utils import InvalidIdTokenError
from fastapi import Request

from rapidfuzz import process, fuzz

import subprocess
import json
import os
from dotenv import load_dotenv

load_dotenv()
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
FIREBASE_JSON_PATH = os.getenv("FIREBASE_JSON_PATH")

app = FastAPI()

# 🔐 Swagger support for Bearer auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
security = HTTPBearer()

#logging
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
        logger.info(
            f"{method} {url} - {response.status_code} | IP: {ip} | UID: {uid} | Email: {email} | UA: {user_agent}"
        )
        return response
    except Exception:
        logger.error(
            f"Unhandled error in {method} {url} | IP: {ip} | UID: {uid} | Email: {email}",
            exc_info=True
        )
        raise

# CORS settings (allow all origins for testing — restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow any frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = os.path.dirname(os.path.abspath(__file__))
# 📂 Define paths for song database
database_dir = os.path.join(base_dir, "song_database")
songs_dir = os.path.join(database_dir, "songs")
metadata_path = os.path.join(database_dir, "songs_metadata.json")
songs_pdf_dir = os.path.join(database_dir, "songs_pdf")

# 🔑 Initialize Firebase Admin using your downloaded private key
cred = credentials.Certificate(FIREBASE_JSON_PATH)
firebase_admin.initialize_app(cred)

# 🔐 Token verification dependency (works with Swagger + API clients)
def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Security(security)):
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


# 🌐 Public route
@app.get("/")
def root():
    return {"message": "FastAPI server is online. No authentication needed."}

# 🔐 Protected route
@app.get("/protected")
def protected_route(user_data=Depends(verify_firebase_token)):
    return {
        "message": "Access granted to protected route!",
        "user": {
            "uid": user_data.get("uid"),
            "email": user_data.get("email")
        }
    }

# GET /songs
def listOfSongs():
    if not os.path.exists(metadata_path):
        print("⚠️ Metadata file not found.")
        return {}

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    songs = {}
    for song_id, filename in metadata.items():
        title = os.path.splitext(filename)[0]  # Remove .pro/.cho extension
        songs[song_id] = title

    return songs

@app.get("/songs")
def songprotected_route(user_data=Depends(verify_firebase_token)):
    return {
        "message": listOfSongs(),
        "user": {
            "uid": user_data.get("uid"),
            "email": user_data.get("email")
        }
    }

# GET /songs/{id}
def specficSong(song_id):
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    if song_id in metadata:
        return metadata[song_id]
    else:
        return "No Song Found with that ID"

@app.get("/songs/{song_id}")
def songIdprotected_route(song_id: str, user_data=Depends(verify_firebase_token)):
    return {
        "message": specficSong(song_id),
        "user": {
            "uid": user_data.get("uid"),
            "email": user_data.get("email")
        }
    }

# Song to PDF (Conversion/Render)
def convert_chordpro_to_pdf(input_file: str, output_file: str):
    print("Running conversion:", input_file, "→", output_file)
    try:
        subprocess.run(
            ["chordpro", input_file, "-o", output_file],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        print("Conversion failed:", e.stderr)
        raise HTTPException(status_code=500, detail=f"ChordPro conversion failed: {e.stderr.strip()}")

def songPDFHelper(song_id: str):
    songInfo = specficSong(song_id)
    if songInfo == "No Song Found with that ID":
        return None

    input_file = os.path.join(songs_dir, songInfo)
    if not os.path.exists(input_file):
        print("Input file not found:", input_file)
        return None

    output_file = os.path.join(songs_pdf_dir, os.path.splitext(songInfo)[0] + ".pdf")
    print("Found input:", input_file)
    print("Target output:", output_file)

    if not os.path.exists(output_file):
        os.makedirs(songs_pdf_dir, exist_ok=True)
        convert_chordpro_to_pdf(input_file, output_file)

    return output_file

@app.get("/songs/{song_id}/pdf")
def song_pdf_protected_route(song_id: str, user_data=Depends(verify_firebase_token)):
    pdf_path = songPDFHelper(song_id)

    if not pdf_path:
        raise HTTPException(status_code=404, detail="No valid ChordPro file found for this ID")

    return FileResponse(
        path=pdf_path,
        filename=os.path.basename(pdf_path),
        media_type="application/pdf"
    )

# Fuzzy search for song: give id
def fuzzySearchSong(song_fuzzy: str):
    songs = listOfSongs()
    title_list = list(songs.values())

    # Run fuzzy matching
    matches = process.extract(song_fuzzy, title_list, scorer=fuzz.WRatio, limit=10)

    # Keep matches with decent score
    filtered = [match for match in matches if match[1] >= 30]  # (title, score, index)

    # Map titles back to ids
    result = []
    for title, score, _ in filtered:
        for song_id, song_title in songs.items():
            if song_title == title:
                result.append({
                    "id": song_id,
                    "title": title,
                    "score": score
                })
                break

    return result

@app.get("/songs/search/{song_fuzzy}")
def songFuzzyRoute(song_fuzzy: str, user_data=Depends(verify_firebase_token)):
    return {
        "message": fuzzySearchSong(song_fuzzy),
        "user": {
            "uid": user_data.get("uid"),
            "email": user_data.get("email")
        }
    }
