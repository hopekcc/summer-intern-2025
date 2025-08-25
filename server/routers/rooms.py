from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from starlette.status import HTTP_401_UNAUTHORIZED
from starlette.responses import FileResponse
from firebase_admin import auth
import datetime
import fitz
import os
import base64

from server.scripts.logger import logger
from server.scripts.database_models import get_room, update_room, create_room_db, generate_room_id_db, log_room_action, delete_room
from server.dependencies import verify_firebase_token, manager
from server.routers.songs import songPDFHelper
from server.dependencies import get_songs_dir, get_songs_pdf_dir, get_metadata_path

router = APIRouter()

# ============================================================================
# SONG DATA HELPER FUNCTIONS
# ============================================================================

def get_song_pdf_path(
    song_id: str,
    songs_dir: str = Depends(get_songs_dir),
    songs_pdf_dir: str = Depends(get_songs_pdf_dir),
    metadata_path: str = Depends(get_metadata_path)
) -> str:
    """Finds the file path for a song's PDF, generating it if it doesn't exist."""
    pdf_path = songPDFHelper(song_id, songs_dir, songs_pdf_dir, metadata_path)
    if not pdf_path or not os.path.exists(pdf_path):
        logger.error(f"PDF for song ID '{song_id}' could not be found or created.")
        raise HTTPException(status_code=404, detail=f"PDF for song ID '{song_id}' not found.")
    return pdf_path

def convert_pdf_to_images(pdf_path: str, page: int = None) -> list[str]:
    """Converts a PDF file into a list of base64 encoded PNG images using PyMuPDF."""
    base64_images = []
    try:
        doc = fitz.open(pdf_path)
        
        start_page = page - 1 if page else 0
        end_page = page if page else doc.page_count
        
        for page_num in range(start_page, end_page):
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

def _get_current_state_payload(
    room_id: str, 
    user_id: str,
    songs_dir: str = Depends(get_songs_dir),
    songs_pdf_dir: str = Depends(get_songs_pdf_dir),
    metadata_path: str = Depends(get_metadata_path)
) -> dict:
    """Helper to generate the data payload for the current room state."""
    room = get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found.")
    
    # Check if the user is a valid participant before sending state
    if user_id not in room.get("participants", []):
        raise HTTPException(status_code=403, detail="You are not a participant in this room.")
    
    song_id = room.get("current_song")
    page = room.get("current_page")
    
    if not song_id or not page:
        return {"type": "state_sync", "message": "No song is currently active in this room."}
    
    try:
        pdf_path = get_song_pdf_path(song_id, songs_dir, songs_pdf_dir, metadata_path)
        logger.info(f"Getting state for room {room_id}, song {song_id}, page {page}, pdf_path: {pdf_path}")
        
        current_image_list = convert_pdf_to_images(pdf_path, page=page)
        total_pages = get_pdf_page_count(pdf_path)
        
        if not current_image_list:
            logger.error(f"No images generated for room {room_id}, song {song_id}, page {page}")
            raise HTTPException(status_code=404, detail="Current page image could not be found.")
        
        logger.info(f"Successfully generated state for room {room_id}: {len(current_image_list)} images, total_pages: {total_pages}")
        
        return {
            "type": "state_sync",
            "song_id": song_id,
            "current_page": page,
            "total_pages": total_pages,
            "image": current_image_list[0]
        }
    except Exception as e:
        logger.error(f"Error in _get_current_state_payload for room {room_id}: {e}", exc_info=True)
        raise

# ============================================================================
# ROOM UPDATE FUNCTIONS
# ============================================================================

def make_song_update(user_id: str, song_id: str):
    def update(room):
        if room["host_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only the host can change the song.")
        room["current_song"] = song_id
        room["current_page"] = 1
        room["last_action"] = {"type": "song_update", "timestamp": datetime.datetime.now(datetime.UTC).isoformat(), "song_id": song_id}
    return update

def make_page_update(user_id: str, page: int):
    def update(room):
        if room["host_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only host can update page")
        room["current_page"] = page
        room["last_action"] = {"type": "page_update", "timestamp": datetime.datetime.now(datetime.UTC).isoformat(), "page": page}
    return update

# ============================================================================
# ROOM MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/create")
def create_room(current_user=Depends(verify_firebase_token)):
    try:
        host_id = current_user['uid']
        room_id = generate_room_id_db()
        room = create_room_db(room_id, host_id)
        return {"room_id": room_id}
    except Exception as e:
        logger.error(f"Failed to create room: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Room creation failed")

@router.post("/join/{room_id}")
def join_room(room_id: str, current_user=Depends(verify_firebase_token)):
    user_id = current_user["uid"]
    
    def join_user_to_room(room, uid):
        if uid not in room["participants"]:
            room["participants"].append(uid)
    
    room = update_room(room_id, lambda r: join_user_to_room(r, user_id))
    
    # Log action separately
    log_room_action(room_id, "user_joined", user_id, {"timestamp": datetime.datetime.now(datetime.UTC).isoformat()})
    
    return room

@router.get("/{room_id}")
def get_room_details(room_id: str, current_user=Depends(verify_firebase_token)):
    room = get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room

@router.post("/{room_id}/leave")
def leave_room(room_id: str, current_user=Depends(verify_firebase_token)):
    user_id = current_user["uid"]
    room = get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    def leave_user_from_room(room, uid):
        if uid in room["participants"]:
            room["participants"].remove(uid)
    
    room = update_room(room_id, lambda r: leave_user_from_room(r, user_id))
    
    # Log action
    log_room_action(room_id, "user_left", user_id, {"timestamp": datetime.datetime.now(datetime.UTC).isoformat()})
    
    # Check if room should be closed
    if not room["participants"] or user_id == room["host_id"]:
        delete_room(room_id)
        logger.info(f"Room {room_id} closed.")
        return {"message": "Host left or room empty. Room closed."}
    
    return {"message": f"User {user_id} left room {room_id}."}

# ============================================================================
# REAL-TIME ACTION ENDPOINTS
# ============================================================================

@router.post("/{room_id}/song")
async def select_song_for_room(
    room_id: str, 
    payload: dict, 
    current_user=Depends(verify_firebase_token),
    songs_dir: str = Depends(get_songs_dir),
    songs_pdf_dir: str = Depends(get_songs_pdf_dir),
    metadata_path: str = Depends(get_metadata_path)
):
    """HOST-ONLY: Sets a new song. Returns ALL images to the host. Broadcasts ONLY THE FIRST page image to participants."""
    try:
        user_id = current_user["uid"]
        song_id = payload.get("song_id")
        if not song_id:
            raise HTTPException(status_code=400, detail="Missing 'song_id' in request body")
        
        update_room(room_id, make_song_update(user_id, song_id))
        
        # Log action
        log_room_action(room_id, "song_update", user_id, {"song_id": song_id, "timestamp": datetime.datetime.now(datetime.UTC).isoformat()})
        
        pdf_path = get_song_pdf_path(song_id, songs_dir, songs_pdf_dir, metadata_path)
        all_images = convert_pdf_to_images(pdf_path)  # Convert all pages
        
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

@router.post("/{room_id}/page")
async def update_room_page(
    room_id: str, 
    payload: dict, 
    current_user=Depends(verify_firebase_token),
    songs_dir: str = Depends(get_songs_dir),
    songs_pdf_dir: str = Depends(get_songs_pdf_dir),
    metadata_path: str = Depends(get_metadata_path)
):
    """HOST-ONLY: Changes the page. Returns a simple confirmation. Broadcasts the NEW page's image to participants."""
    try:
        user_id = current_user["uid"]
        page = payload.get("page")
        if not isinstance(page, int) or page < 1:
            raise HTTPException(status_code=400, detail="A valid 'page' number is required.")
        
        room = get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found.")
        song_id = room.get("current_song")
        if not song_id:
            raise HTTPException(status_code=400, detail="No song is active.")
        
        update_room(room_id, make_page_update(user_id, page))
        
        # Log action
        log_room_action(room_id, "page_update", user_id, {"page": page, "timestamp": datetime.datetime.now(datetime.UTC).isoformat()})
        
        pdf_path = get_song_pdf_path(song_id, songs_dir, songs_pdf_dir, metadata_path)
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

# ============================================================================
# PARTICIPANT DATA-FETCHING ENDPOINTS
# ============================================================================

@router.get("/{room_id}/current")
def get_current_room_state(
    room_id: str, 
    current_user=Depends(verify_firebase_token),
    songs_dir: str = Depends(get_songs_dir),
    songs_pdf_dir: str = Depends(get_songs_pdf_dir),
    metadata_path: str = Depends(get_metadata_path)
):
    """PARTICIPANT: Gets everything needed to sync their view upon joining."""
    try:
        return _get_current_state_payload(room_id, current_user["uid"], songs_dir, songs_pdf_dir, metadata_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current state error for room {room_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve current room state.")

@router.get("/{room_id}/pdf")
def download_room_pdf(
    room_id: str, 
    current_user=Depends(verify_firebase_token),
    songs_dir: str = Depends(get_songs_dir),
    songs_pdf_dir: str = Depends(get_songs_pdf_dir),
    metadata_path: str = Depends(get_metadata_path)
):
    room = get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    song_id = room.get("current_song")
    if not song_id:
        raise HTTPException(status_code=400, detail="No song selected for this room")
    pdf_path = get_song_pdf_path(song_id, songs_dir, songs_pdf_dir, metadata_path)
    return FileResponse(path=pdf_path, filename=os.path.basename(pdf_path), media_type="application/pdf")

# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    # Accept the WebSocket connection first
    await websocket.accept()
    try:
        # Get authentication token from client
        token = await websocket.receive_text()
        
        # Verify the token
        try:
            decoded_token = auth.verify_id_token(token)
            user_id = decoded_token["uid"]
        except Exception as auth_error:
            await websocket.close(code=4001, reason=f"Invalid auth token: {auth_error}")
            return
        
        # Verify user is a participant in this room BEFORE connecting
        room = get_room(room_id)
        if not room:
            await websocket.close(code=4004, reason="Room not found")
            return
        if user_id not in room["participants"]:
            await websocket.close(code=4003, reason="Not a participant in this room")
            return
        
        await manager.connect(room_id, websocket)
        
        try:
            # Manually instantiate dependencies for the WebSocket context
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
            # This is a bit of a hack because Depends() doesn't work in WebSocket routes
            # We assume a similar structure to how dependencies resolve paths
            # This should be made more robust in a real application
            
            # Construct test paths if 'test' is in the path, otherwise construct real paths
            # This is still not ideal. A better solution is a factory or context var.
            is_test_env = "tests" in base_dir

            if is_test_env:
                test_song_db_path = os.path.abspath(os.path.join(base_dir, "..", "tests", "test_song_database"))
                songs_dir = os.path.join(test_song_db_path, "songs")
                songs_pdf_dir = os.path.join(test_song_db_path, "songs_pdf")
                metadata_path = os.path.join(test_song_db_path, "songs_metadata.json")
            else:
                # Assuming the 'server' directory is the root for these paths
                # This may need adjustment based on your actual project structure
                real_song_db_path = os.path.join(base_dir, "..", "song_database")
                songs_dir = os.path.join(real_song_db_path, "songs")
                songs_pdf_dir = os.path.join(real_song_db_path, "songs_pdf")
                metadata_path = os.path.join(real_song_db_path, "songs_metadata.json")

            initial_state = _get_current_state_payload(room_id, user_id, songs_dir, songs_pdf_dir, metadata_path)
            await websocket.send_json(initial_state)
        except Exception as state_error:
            logger.error(f"Failed to send initial state to user {user_id} in room {room_id}: {state_error}")
        
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        logger.info(f"WebSocket disconnected from room {room_id}")
    except Exception as e:
        logger.error(f"WebSocket error in room {room_id}: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
        manager.disconnect(room_id, websocket) 