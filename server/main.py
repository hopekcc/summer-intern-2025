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
from fastapi import File, UploadFile

from scripts.logger import logger
from firebase_admin import auth
from firebase_admin._auth_utils import InvalidIdTokenError
from fastapi import Request

from rapidfuzz import process, fuzz

from fastapi import WebSocket

import datetime
import fitz

import subprocess
import json
import os
from dotenv import load_dotenv

from pdf2image import convert_from_bytes, pdfinfo_from_bytes
import base64
import io

from utils import ConnectionManager

import random
import string

load_dotenv()
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
FIREBASE_JSON_PATH = os.getenv("FIREBASE_JSON_PATH")

app = FastAPI()

# 🔐 Swagger support for Bearer auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
security = HTTPBearer()

manager = ConnectionManager()


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
        "message": listOfSongs()
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
        "message": specficSong(song_id)
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
        "message": fuzzySearchSong(song_fuzzy)
    }
# =======================================================================
# ROOM DATABASE HELPERS
# =======================================================================

# Room database file path
room_database_file = os.path.join(base_dir, "room_database", "rooms.json")

def load_rooms():
    """Loads the entire rooms database from the JSON file."""
    try:
        if not os.path.exists(os.path.dirname(room_database_file)):
            os.makedirs(os.path.dirname(room_database_file))
        if not os.path.exists(room_database_file) or os.path.getsize(room_database_file) == 0:
            with open(room_database_file, "w") as f:
                json.dump({}, f)
            return {}
        with open(room_database_file, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading rooms: {e}", exc_info=True)
        return {}

def save_rooms(rooms):
    """Saves the entire rooms database to the JSON file."""
    try:
        with open(room_database_file, "w") as f:
            json.dump(rooms, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving rooms: {e}", exc_info=True)

def generate_room_id(length=6):
    """Generates a unique 6-character ID for a new room."""
    rooms = load_rooms()
    while True:
        room_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if room_id not in rooms:
            break
    return room_id

# =======================================================================
# >>>>> THE MISSING FUNCTION IS HERE <<<<<
# This function is essential for safely modifying the room database.
# =======================================================================
def update_room(room_id: str, update_func):
    """
    Atomically loads, modifies, and saves the room database.

    Args:
        room_id: The ID of the room to modify.
        update_func: A function that takes a room dictionary and modifies it.

    Returns:
        The updated room dictionary.
    """
    rooms = load_rooms()
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    update_func(room)  # The provided function modifies the room object

    rooms[room_id] = room
    save_rooms(rooms)
    return room

# =======================================================================
# REUSABLE SONG DATA HELPER FUNCTIONS
# =======================================================================

def get_song_pdf_path(song_id: str) -> str:
    """Finds the file path for a song's PDF, generating it if it doesn't exist."""
    pdf_path = songPDFHelper(song_id)
    if not pdf_path or not os.path.exists(pdf_path):
        logger.error(f"PDF for song ID '{song_id}' could not be found or created.")
        raise HTTPException(status_code=404, detail=f"PDF for song ID '{song_id}' not found.")
    return pdf_path

def convert_pdf_to_images(pdf_path: str, page: int = None) -> list[str]:
    """
    Converts a PDF file into a list of base64 encoded PNG images using PyMuPDF.

    Args:
        pdf_path: The full path to the PDF file.
        page: If specified (1-indexed), converts only that single page.
              If None, converts all pages.
    """
    base64_images = []
    try:
        doc = fitz.open(pdf_path)
        
        start_page = page - 1 if page else 0
        end_page = page if page else doc.page_count

        for page_num in range(start_page, end_page):
            # pix.tobytes() returns the image data as PNG by default
            pix = doc[page_num].get_pixmap()
            img_bytes = pix.tobytes()
            img_str = base64.b64encode(img_bytes).decode("utf-8")
            base64_images.append("data:image/png;base64," + img_str)
            
        doc.close()
    except Exception as e:
        logger.error(f"Failed during PyMuPDF conversion for {pdf_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to render song pages.")
        
    return base64_images

def get_pdf_page_count(pdf_path: str) -> int:
    """Gets the total number of pages in a PDF using PyMuPDF."""
    try:
        doc = fitz.open(pdf_path)
        count = doc.page_count
        doc.close()
        return count
    except Exception as e:
        logger.error(f"Could not get page count for {pdf_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve song page count.")
    
def _get_current_state_payload(room_id: str, user_id: str) -> dict:
    """
    A reusable helper to generate the data payload for the current room state.
    This is now used by both the HTTP endpoint and the WebSocket on-connect event.
    """
    rooms = load_rooms()
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found.")
    room = rooms[room_id]
    
    # Check if the user is a valid participant before sending state
    if user_id not in room.get("participants", []):
        raise HTTPException(status_code=403, detail="You are not a participant in this room.")

    song_id = room.get("current_song")
    page = room.get("current_page")

    if not song_id or not page:
        return {"type": "state_sync", "message": "No song is currently active in this room."}

    pdf_path = get_song_pdf_path(song_id)
    current_image_list = convert_pdf_to_images(pdf_path, page=page)
    total_pages = get_pdf_page_count(pdf_path)

    if not current_image_list:
        raise HTTPException(status_code=404, detail="Current page image could not be found.")

    return {
        "type": "state_sync", # Use a clear type for this initial payload
        "song_id": song_id,
        "current_page": page,
        "total_pages": total_pages,
        "image": current_image_list[0]
    }


# =======================================================================
# FINALIZED ROOM ENDPOINTS
# =======================================================================

def make_song_update(user_id: str, song_id: str):
    # ... (This function is correct)
    def update(room):
        if room["host_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only the host can change the song.")
        room["current_song"] = song_id
        room["current_page"] = 1
        room["last_action"] = { "type": "song_update", "timestamp": datetime.datetime.now(datetime.UTC).isoformat(), "song_id": song_id }
    return update

def make_page_update(user_id: str, page: int):
    # ... (This function is correct)
    def update(room):
        if room["host_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only host can update page")
        room["current_page"] = page
        room["last_action"] = { "type": "page_update", "timestamp": datetime.datetime.now(datetime.UTC).isoformat(), "page": page }
    return update

### --- Room Lifecycle and Metadata Endpoints ---

@app.post("/rooms/create")
def create_room(current_user=Depends(verify_firebase_token)):
    # ... (This function is correct)
    try:
        host_id = current_user['uid']       
        room_id = generate_room_id()
        rooms = load_rooms()
        rooms[room_id] = {
           "host_id": host_id,
           "participants": [host_id],
           "current_song": None,
           "current_page": None,
           "last_action": { "type": "room_created", "timestamp":  datetime.datetime.now(datetime.UTC).isoformat() }
        }
        save_rooms(rooms)
        return {"room_id": room_id}
    except Exception as e:
       logger.error(f"Failed to create room: {e}", exc_info=True)
       raise HTTPException(status_code=500, detail="Room creation failed")

@app.post("/rooms/join/{room_id}")
def join_room(room_id: str, current_user=Depends(verify_firebase_token)):
    # This now works because update_room exists.
    user_id = current_user["uid"]
    def join_user_to_room(room, uid):
        if uid not in room["participants"]:
            room["participants"].append(uid)
            room["last_action"] = { "type": "user_joined", "timestamp": datetime.datetime.now(datetime.UTC).isoformat(), "user_id": uid }
    room = update_room(room_id, lambda r: join_user_to_room(r, user_id))
    return room

@app.get("/rooms/{room_id}")
def get_room_details(room_id: str, current_user=Depends(verify_firebase_token)):
    # ... (This function is correct)
    rooms = load_rooms()
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return rooms[room_id]

@app.post("/rooms/{room_id}/leave")
def leave_room(room_id: str, current_user=Depends(verify_firebase_token)):
    # ... (This function is correct)
    user_id = current_user["uid"]
    rooms = load_rooms()
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    room = rooms[room_id]
    if user_id in room["participants"]:
        room["participants"].remove(user_id)
    if not room["participants"] or user_id == room["host_id"]:
        del rooms[room_id]
        logger.info(f"Room {room_id} closed.")
        save_rooms(rooms)
        return {"message": "Host left or room empty. Room closed."}
    room["last_action"] = { "type": "user_left", "timestamp": datetime.datetime.now(datetime.UTC).isoformat(), "user_id": user_id }
    rooms[room_id] = room
    save_rooms(rooms)
    return {"message": f"User {user_id} left room {room_id}."}

### --- Real-Time Action Endpoints ---
@app.post("/rooms/{room_id}/song")
# ... (This endpoint now works correctly because it calls the new helper functions)
async def select_song_for_room(room_id: str, payload: dict, current_user=Depends(verify_firebase_token)):
    """
    HOST-ONLY: Sets a new song. Returns ALL images to the host.
    Broadcasts ONLY THE FIRST page image to participants.
    """
    try:
        user_id = current_user["uid"]
        song_id = payload.get("song_id")
        if not song_id:
            raise HTTPException(status_code=400, detail="Missing 'song_id' in request body")
        
        update_room(room_id, make_song_update(user_id, song_id))
        
        pdf_path = get_song_pdf_path(song_id)
        all_images = convert_pdf_to_images(pdf_path) # Convert all pages

        if not all_images:
             raise HTTPException(status_code=500, detail="Song rendering produced no images.")

        # Broadcast the FIRST page to participants
        await manager.broadcast(room_id, {
            "type": "song_update",
            "song_id": song_id,
            "image": all_images[0]
        })

        # Return the FULL set of images to the host for preloading
        return {"images": all_images}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Select song error for room {room_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to set song.")

@app.post("/rooms/{room_id}/page")
# ... (This endpoint now works correctly because it calls the new helper functions)
async def update_room_page(room_id: str, payload: dict, current_user=Depends(verify_firebase_token)):
    """
    HOST-ONLY: Changes the page. Returns a simple confirmation.
    Broadcasts the NEW page's image to participants.
    """
    try:
        user_id = current_user["uid"]
        page = payload.get("page")
        if not isinstance(page, int) or page < 1:
            raise HTTPException(status_code=400, detail="A valid 'page' number is required.")

        rooms = load_rooms()
        if room_id not in rooms: raise HTTPException(status_code=404, detail="Room not found.")
        song_id = rooms[room_id].get("current_song")
        if not song_id: raise HTTPException(status_code=400, detail="No song is active.")
        
        update_room(room_id, make_page_update(user_id, page))
        
        pdf_path = get_song_pdf_path(song_id)
        page_image_list = convert_pdf_to_images(pdf_path, page=page)
        
        if not page_image_list:
            raise HTTPException(status_code=404, detail=f"Page {page} could not be rendered.")

        await manager.broadcast(room_id, {
            "type": "page_update",
            "page": page,
            "image": page_image_list[0]
        })
        return {"message": "Page update broadcasted."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update page error for room {room_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update page.")

### --- Participant Data-Fetching Endpoints ---
@app.get("/rooms/{room_id}/current")
def get_current_room_state(room_id: str, current_user=Depends(verify_firebase_token)):
    """
    PARTICIPANT: Gets everything needed to sync their view upon joining.
    This endpoint now calls the reusable helper function.
    """
    try:
        # The helper function contains all the necessary logic and error handling.
        return _get_current_state_payload(room_id, current_user["uid"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current state error for room {room_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve current room state.")
    
@app.get("/rooms/{room_id}/pdf")
def download_room_pdf(room_id: str, current_user=Depends(verify_firebase_token)):
    # ... (This function is correct)
    rooms = load_rooms()
    if room_id not in rooms: raise HTTPException(status_code=404, detail="Room not found")
    song_id = rooms[room_id].get("current_song")
    if not song_id: raise HTTPException(status_code=400, detail="No song selected for this room")
    pdf_path = get_song_pdf_path(song_id)
    return FileResponse(path=pdf_path, filename=os.path.basename(pdf_path), media_type="application/pdf")

### --- WebSocket Connection Endpoint ---

@app.websocket("/ws/rooms/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    # This endpoint is now smarter.
    await manager.connect(room_id, websocket)
    
    # We need a token to identify the user for the initial state push.
    # The client should pass this as a query parameter or subprotocol.
    # For simplicity, let's assume an initial message from the client with the token.
    try:
        # 1. Immediately send the current state to the newly connected client
        # To do this safely, we need to know who the user is.
        # A common pattern is for the client to send its token as the first message.
        token = await websocket.receive_text()
        try:
            decoded_token = auth.verify_id_token(token)
            user_id = decoded_token["uid"]
            
            # Now, get and send the current state payload
            initial_state = _get_current_state_payload(room_id, user_id)
            await websocket.send_json(initial_state)

        except Exception as auth_error:
            # If token is invalid, close the connection
            await websocket.close(code=4001, reason=f"Invalid auth token: {auth_error}")
            manager.disconnect(room_id, websocket)
            return

        # 2. Now, listen for future broadcasted updates for this client
        while True:
            # This loop keeps the connection alive to receive broadcasts from the manager
            await websocket.receive_text() # Can be used for pings/pongs if needed
            
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        logger.info(f"WebSocket disconnected from room {room_id}")


