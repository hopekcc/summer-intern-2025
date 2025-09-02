import asyncio
from scripts.runtime.logger import logger as _app_logger
import os
import time
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib

from scripts.runtime.paths import get_songs_pdf_dir, get_songs_img_dir
from scripts.runtime.database import (
    Room, RoomParticipant, User, Song, get_db_session,
    get_room_by_id_from_db, get_song_by_id_from_db,
    create_room_db, delete_room, add_participant, remove_participant,
    generate_room_id, get_room, log_room_action
)
from scripts.runtime.auth_middleware import get_current_user, get_room_access, get_host_access
# Song model now imported from unified database above
from scripts.runtime.websocket_server import get_websocket_factory

router = APIRouter()
logger = _app_logger.getChild("api.rooms")

# Response Models - Document actual output structure
class RoomResponse(BaseModel):
    room_id: str = Field(..., description="Unique room identifier", example="0x1a2b3c4d")

class JoinRoomResponse(BaseModel):
    message: str = Field(..., description="Success message", example="User user123 joined room 0x1a2b3c4d")

class RoomDetailsResponse(BaseModel):
    room_id: str = Field(..., description="Room identifier", example="0x1a2b3c4d")
    host_id: str = Field(..., description="Host user ID", example="user123")
    current_song: Optional[str] = Field(None, description="Current song ID", example="400")
    current_page: Optional[int] = Field(None, description="Current page number", example=1)
    participants: List[str] = Field(..., description="List of participant user IDs", example=["user123", "user456"])

# Request Models - Document request body structure
class SelectSongRequest(BaseModel):
    song_id: str = Field(..., description="ID of the song to select for the room", example="400")

class UpdatePageRequest(BaseModel):
    page: int = Field(..., description="Page number to update to", example=2)

class LeaveRoomResponse(BaseModel):
    message: str = Field(..., description="Leave room result message", example="User user123 left room 0x1a2b3c4d")

class SelectSongResponse(BaseModel):
    message: str = Field(..., description="Song selection result", example="Song selected successfully")
    song_id: str = Field(..., description="Selected song ID", example="400")
    title: str = Field(..., description="Song title", example="Amazing Grace")
    artist: str = Field(..., description="Song artist", example="John Newton")
    total_pages: int = Field(..., description="Total pages in song", example=3)
    current_page: int = Field(..., description="Current page number", example=1)
    image_etag: str = Field(..., description="ETag for current page image", example="W/\"abc123-1234567890\"")

class UpdatePageResponse(BaseModel):
    message: str = Field(..., description="Page update result", example="Page update broadcasted.")

# ===================================================================
# HTTP Endpoints - Now fully asynchronous
# ===================================================================

# ----------------------------------------------------------------------------
# Strong ETag helpers for images (BLAKE2b with configurable digest size)
# ----------------------------------------------------------------------------

_ETAG_BITS = os.getenv("ETAG_BITS", "128")
try:
    _ETAG_BITS_INT = int(_ETAG_BITS)
    if _ETAG_BITS_INT not in (64, 128, 256):
        _ETAG_BITS_INT = 128
except Exception:
    _ETAG_BITS_INT = 128

_ETAG_CACHE: Dict[Tuple[str, int, int, int], str] = {}

def _blake2b_hexdigest(path: str, digest_bits: int) -> str:
    st = os.stat(path)
    key = (path, st.st_size, int(st.st_mtime), digest_bits)
    cached = _ETAG_CACHE.get(key)
    if cached:
        return cached
    digest_size = digest_bits // 8
    h = hashlib.blake2b(digest_size=digest_size)
    # Read in chunks to minimize memory
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    etag = h.hexdigest()
    _ETAG_CACHE[key] = etag
    return etag

## Deterministic image layout: songs_img/{song_id}/page_{page}.webp
## We no longer probe candidates; callers build the path directly and handle errors.

@router.post("/", 
    response_model=RoomResponse,
    responses={
        401: {"description": "Authentication required"},
        500: {"description": "Could not create room"}
    }
)
async def create_room(request: Request, host_data = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    start_time = time.perf_counter()
    host_id = host_data['uid']
    try:
        # Clean up any existing rooms for this host first
        cleanup_start = time.perf_counter()
        try:
            # Find existing rooms hosted by this user
            existing_rooms_result = await session.execute(
                select(Room).where(Room.host_id == host_id)
            )
            existing_rooms = existing_rooms_result.scalars().all()
            
            if existing_rooms:
                logger.info(f"Cleaning up {len(existing_rooms)} existing rooms for host {host_id}")
                
                # Get WebSocket factory for notifications
                ws_factory = get_websocket_factory()
                
                for old_room in existing_rooms:
                    # Notify participants that room is closing
                    if ws_factory:
                        try:
                            ws_factory.register_room(old_room.room_id)
                            asyncio.create_task(ws_factory.broadcast_to_room(old_room.room_id, {
                                "type": "room_closed",
                                "room_id": old_room.room_id,
                                "reason": "Host created new room"
                            }))
                        except Exception:
                            logger.warning("Failed to notify room closure", exc_info=True, extra={"room_id": old_room.room_id})
                    
                    # Delete the room (this also deletes participants via cascade or helper)
                    await delete_room(session, old_room)
                
                cleanup_elapsed = (time.perf_counter() - cleanup_start) * 1000
                logger.info(f"CLEANUP_OLD_ROOMS duration={cleanup_elapsed:.1f}ms count={len(existing_rooms)}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old rooms for host {host_id}: {e}", exc_info=True)
            # Continue with room creation even if cleanup fails
        
        # Create new room
        room_id = generate_room_id()
        new_room = await create_room_db(session, room_id, host_id)
        await session.commit()  # Commit the room creation and cleanup
        
        # Pre-register WS room to avoid warnings before any client joins
        try:
            ws_factory = get_websocket_factory()
            if ws_factory:
                ws_factory.register_room(room_id)
        except Exception:
            logger.warning("Failed to pre-register WS room on create", exc_info=True, extra={"room_id": room_id})
        
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(f"CREATE_ROOM total={elapsed:.1f}ms room={room_id}")
        # Return room_id directly to avoid lazy loading after session commit
        return {"room_id": room_id}
    except Exception as e:
        logger.error(f"Failed to create room for host {host_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not create room.")

@router.post("/{room_id}/join", 
    response_model=JoinRoomResponse,
    responses={
        404: {"description": "Room not found"},
        401: {"description": "Authentication required"},
        500: {"description": "Could not join room"}
    }
)
async def join_room(room_id: str, room_and_user = Depends(get_room_access), session: AsyncSession = Depends(get_db_session)):
    start_time = time.perf_counter()
    room, user_id = room_and_user
    try:
        db_start = time.perf_counter()
        await add_participant(session, room_id, user_id)
        await session.commit()  # Commit the participant addition
        db_elapsed = (time.perf_counter() - db_start) * 1000
        logger.info(f"ADD_PARTICIPANT db={db_elapsed:.1f}ms")
        
        # Notify room participants via WebSocket
        ws_factory = get_websocket_factory()
        if ws_factory:
            # Ensure room is known to WS factory (useful after server restarts)
            try:
                ws_factory.register_room(room_id)
            except Exception:
                logger.warning("WS register_room failed in join_room", exc_info=True, extra={"room_id": room_id})
            asyncio.create_task(ws_factory.broadcast_to_room(room_id, {
                "type": "participant_joined",
                "user_id": user_id
            }))
            logger.info(f"Queued participant_joined event for user {user_id} in room {room_id} via WebSocket")
        else:
            logger.warning(f"WebSocket factory not available, could not send participant_joined event")
        
        total_elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(f"JOIN_ROOM total={total_elapsed:.1f}ms")
        return {"message": f"User {user_id} joined room {room_id}"}
    except HTTPException as e:
        # Do not convert expected 4xx into 500s
        raise e
    except Exception as e:
        logger.error(f"Failed to join room {room_id} for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not join room.")

@router.post("/{room_id}/leave", 
    response_model=LeaveRoomResponse,
    responses={
        404: {"description": "Room not found"},
        401: {"description": "Authentication required"},
        500: {"description": "Could not leave room"}
    }
)
async def leave_room(room_id: str, room_and_user = Depends(get_room_access), session: AsyncSession = Depends(get_db_session)):
    room, user_id = room_and_user
    try:
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        # Avoid relationship lazy load; explicitly verify membership
        membership_result = await session.execute(
            select(RoomParticipant).where(
                RoomParticipant.room_id == room_id,
                RoomParticipant.user_id == user_id
            )
        )
        if not membership_result.scalars().first():
            raise HTTPException(status_code=400, detail="User is not in this room")

        is_host = (user_id == room.host_id)
        await remove_participant(session, room_id, user_id)
        await log_room_action(session, room_id, "participant_left", user_id)

        # Determine if room should be closed without triggering lazy load
        participants_result = await session.execute(
            select(RoomParticipant).where(RoomParticipant.room_id == room_id)
        )
        remaining_participants = participants_result.scalars().all()

        # Get WebSocket factory
        ws_factory = get_websocket_factory()

        if is_host or len(remaining_participants) == 0:
            logger.info(f"Host {user_id} left or room is empty. Closing room {room_id}.")
            current_room = await get_room(session, room_id)
            if current_room:
                await delete_room(session, current_room)  # helper no longer commits
            await session.commit()

            # Notify room closure via WebSocket
            if ws_factory:
                try:
                    ws_factory.register_room(room_id)
                except Exception:
                    logger.warning("WS register_room failed in leave_room(room_closed)", exc_info=True, extra={"room_id": room_id})
                asyncio.create_task(ws_factory.broadcast_to_room(room_id, {
                    "type": "room_closed",
                    "room_id": room_id
                }))
                logger.info(f"Queued room_closed event for room {room_id} via WebSocket")
            else:
                logger.warning(f"WebSocket factory not available, could not send room_closed event")
            message = "Host left, room closed"
        else:
            # Persist participant removal before notifying
            await session.commit()

            # Notify participant left via WebSocket
            if ws_factory:
                try:
                    ws_factory.register_room(room_id)
                except Exception:
                    logger.warning("WS register_room failed in leave_room(participant_left)", exc_info=True, extra={"room_id": room_id})
                asyncio.create_task(ws_factory.broadcast_to_room(room_id, {
                    "type": "participant_left",
                    "user_id": user_id
                }))
                logger.info(f"Queued participant_left event for user {user_id} in room {room_id} via WebSocket")
            else:
                logger.warning(f"WebSocket factory not available, could not send participant_left event")
            message = f"User {user_id} left room {room_id}"

        return {"message": message}
    except HTTPException as e:
        # Do not convert expected 4xx into 500s
        raise e
    except Exception as e:
        logger.error(f"Failed to leave room {room_id} for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not leave room.")

@router.get("/{room_id}", 
    response_model=RoomDetailsResponse,
    responses={
        404: {"description": "Room not found"}
    }
)
async def get_room_details(room_id: str, session: AsyncSession = Depends(get_db_session)):
    room = await get_room_by_id_from_db(session, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Explicitly load participants to avoid async context issues
    result = await session.execute(select(RoomParticipant).where(RoomParticipant.room_id == room_id))
    participants = result.scalars()
    participant_list = [p.user_id for p in participants.all()]
    
    return {
        "room_id": room.room_id,
        "host_id": room.host_id,
        "current_song": room.current_song,
        "current_page": room.current_page,
        "participants": participant_list
    }

@router.post("/{room_id}/song", 
    response_model=SelectSongResponse,
    responses={
        404: {"description": "Room or song not found"},
        401: {"description": "Authentication required (host only)"},
        500: {"description": "Could not select song"}
    }
)
async def select_song_for_room(
    room_id: str,
    request: SelectSongRequest,
    room_and_user = Depends(get_host_access),
    session: AsyncSession = Depends(get_db_session),
    songs_pdf_dir: str = Depends(get_songs_pdf_dir),
    songs_img_dir: str = Depends(get_songs_img_dir)
):
    song_id = request.song_id
    room, host_id = room_and_user

    try:
        # Get song details from unified database using async session
        song = await get_song_by_id_from_db(session, song_id)
        
        if not song:
            raise HTTPException(status_code=404, detail=f"Song with ID '{song_id}' not found")

        # Extract song data immediately to avoid accessing after session operations
        song_title = song.title
        song_artist = song.artist
        song_filename = song.filename
        song_page_count = song.page_count

        # Verify the PDF exists (prefer ID-based PDF, fallback to legacy filename-based)
        pdf_path = os.path.join(songs_pdf_dir, f"{song.id}.pdf")
        if not os.path.exists(pdf_path):
            if song_filename:
                legacy_name = f"{os.path.splitext(song_filename)[0]}.pdf"
                legacy_path = os.path.join(songs_pdf_dir, legacy_name)
                if os.path.exists(legacy_path):
                    pdf_path = legacy_path
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="Song PDF not found. The song may not have been properly preloaded.")

        # Update room state - fetch room in current session without eager loading
        result = await session.execute(select(Room).where(Room.room_id == room_id))
        current_room = result.scalars().first()
        if not current_room:
            raise HTTPException(status_code=404, detail="Room not found")
            
        current_room.current_song = song.id
        current_room.current_page = 1
        session.add(current_room)
        
        # Batch commit with room creation if needed
        await session.commit()
        # Remove expensive refresh - data already available

        # 5. Compute image ETag for page 1 (metadata only) using weak ETag (size-mtime)
        image_etag = None
        try:
            image_path = os.path.join(songs_img_dir, song.id, f"page_{1}.webp")
            logger.info(f"Song selection - Using image path: {image_path} (song_id: {song.id})")
            st = os.stat(image_path)
            image_etag = f"W/\"{st.st_size:x}-{int(st.st_mtime)}\""
        except Exception as e:
            logger.error(f"Failed to compute image ETag for song selection: {e}")
            # Set a default ETag to prevent null values in WebSocket messages
            image_etag = f"error-{int(time.time())}"
        
        # Get WebSocket factory
        ws_factory = get_websocket_factory()
        if not ws_factory:
            logger.warning(f"WebSocket factory not available, could not send song update events")
            # Fallback to returning the data via HTTP
            return {
                "message": "Song selected successfully (WebSocket unavailable)",
                "song_id": song.id,
                "title": song_title,
                "artist": song_artist,
                "total_pages": song_page_count,
                "current_page": 1,
                "image_etag": image_etag,
            }
        
        # Metadata-only payload; clients fetch image over HTTP when ETag changes
        song_update_payload = {
            'song_id': song.id,
            'title': song_title,
            'artist': song_artist,
            'total_pages': song_page_count,
            'current_page': 1,
            'image_etag': image_etag,
        }
        
        # Send song update via WebSocket (metadata only)
        if ws_factory:
            try:
                ws_factory.register_room(room_id)
            except Exception:
                logger.warning("WS register_room failed in select_song_for_room", exc_info=True, extra={"room_id": room_id})
            asyncio.create_task(ws_factory.broadcast_song_updated(room_id, song_update_payload))
        
        # Return fast response without image data
        return {"message": "Song selected successfully", **song_update_payload}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to select song {song_id} for room {room_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{room_id}/page", 
    response_model=UpdatePageResponse,
    responses={
        404: {"description": "Room not found"},
        401: {"description": "Authentication required (host only)"},
        400: {"description": "Invalid page number"},
        500: {"description": "Could not update page"}
    }
)
async def update_page_for_room(room_id: str, request: UpdatePageRequest, host_data = Depends(get_host_access), session: AsyncSession = Depends(get_db_session), songs_img_dir: str = Depends(get_songs_img_dir)):
    page = request.page
    room, host_id = host_data
    
    try:
        
        if not isinstance(page, int) or page < 1:
            raise HTTPException(status_code=400, detail={
                "code": "PAGE_INVALID",
                "message": "A valid 'page' number is required."
            })
        # Load and update the room in the current session to persist page change
        result = await session.execute(select(Room).where(Room.room_id == room_id))
        current_room = result.scalars().first()
        if not current_room:
            raise HTTPException(status_code=404, detail="Room not found")

        # DB-backed bounds check: if a song is selected, ensure page is within 1..page_count
        song = None
        if current_room.current_song:
            song = await get_song_by_id_from_db(session, current_room.current_song)
            total_pages = max(1, int(getattr(song, 'page_count', 1) or 1))
            if page > total_pages:
                raise HTTPException(status_code=400, detail={
                    "code": "PAGE_OUT_OF_RANGE",
                    "message": f"Page {page} is out of range (1..{total_pages})"
                })

        # Persist the new page number
        current_room.current_page = page
        session.add(current_room)

        # Log the action in the same transaction
        await log_room_action(session, room_id, "page_updated", host_id, {"page": page})

        # Commit state change and log entry
        await session.commit()

        # Get song details and compute image ETag (metadata only) based on updated state
        song_details = None
        image_etag = None
        if current_room.current_song:
            try:
                # song may have been loaded for bounds check; reuse it if available
                if song is None:
                    song = await get_song_by_id_from_db(session, current_room.current_song)
                song_details = {
                    'id': song.id,
                    'title': song.title,
                    'artist': song.artist,
                    'total_pages': getattr(song, 'page_count', 1)
                }
                image_path = os.path.join(songs_img_dir, song.id, f"page_{page}.webp")
                logger.info(f"Using image path: {image_path} (song_id: {song.id})")
                st = os.stat(image_path)
                image_etag = f"W/\"{st.st_size:x}-{int(st.st_mtime)}\""
            except Exception as e:
                logger.error(f"Failed to get song details for page update: {e}")
                # Set a default ETag to prevent null values in WebSocket messages
                image_etag = f"error-{int(time.time())}"

        # Create payload with song metadata
        page_update_payload = {
            "current_page": page,
            "song_id": current_room.current_song,
            "title": song_details['title'] if song_details else 'Unknown',
            "artist": song_details['artist'] if song_details else 'Unknown',
            "total_pages": song_details['total_pages'] if song_details else 1,
            "image_etag": image_etag,
        }
        
        # Send page update via WebSocket (metadata only)
        ws_factory = get_websocket_factory()
        if ws_factory:
            try:
                ws_factory.register_room(room_id)
            except Exception:
                logger.warning("WS register_room failed in update_room_page", exc_info=True, extra={"room_id": room_id})
            asyncio.create_task(ws_factory.broadcast_page_updated(room_id, page_update_payload))
        else:
            logger.warning(f"WebSocket factory not available, could not send page_updated event")

        return {"message": "Page update broadcasted."}
    except HTTPException as e:
        # Propagate expected HTTP errors (e.g., 400 out-of-range) without converting to 500
        raise e
    except Exception as e:
        logger.error(f"Failed to update page for room {room_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not update page.")

@router.get("/{room_id}/pdf",
    responses={
        404: {"description": "Room, song, or PDF not found"},
        401: {"description": "Authentication required"},
        200: {"description": "PDF file", "content": {"application/pdf": {}}}
    }
)
async def download_room_pdf(room_id: str, request: Request, room_and_user = Depends(get_room_access), session: AsyncSession = Depends(get_db_session)):
    try:
        room, user_id = room_and_user
        if not room.current_song:
            raise HTTPException(status_code=404, detail="No current song in this room")

        # Get song details from the songs database
        song = await get_song_by_id_from_db(session, room.current_song)
        
        # Prefer ID-based PDF name with legacy filename-based fallback
        base_dir = request.app.state.songs_pdf_dir
        pdf_path = os.path.join(base_dir, f"{song.id}.pdf")
        if not os.path.exists(pdf_path) and song.filename:
            legacy_name = f"{os.path.splitext(song.filename)[0]}.pdf"
            legacy_path = os.path.join(base_dir, legacy_name)
            if os.path.exists(legacy_path):
                pdf_path = legacy_path
        
        if os.path.exists(pdf_path):
            st = os.stat(pdf_path)
            headers = {
                "Cache-Control": "public, max-age=86400",
                "ETag": f"W/\"{st.st_size:x}-{int(st.st_mtime)}\"",
            }
            return FileResponse(path=pdf_path, filename=os.path.basename(pdf_path), media_type="application/pdf", headers=headers)
        else:
            raise HTTPException(status_code=404, detail="Song PDF not found. The song may not have been properly preloaded.")
    except HTTPException as e:
        # Propagate 4xx as-is
        raise e
    except Exception as e:
        logger.error(f"Failed to download PDF for room {room_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not download PDF.")

@router.get("/{room_id}/image",
    responses={
        404: {"description": "Room, song, or image not found"},
        401: {"description": "Authentication required"},
        304: {"description": "Image not modified (ETag match)"},
        200: {"description": "Image data", "content": {"image/png": {}}}
    }
)
async def get_room_image(room_id: str, request: Request, room_and_user = Depends(get_room_access), session: AsyncSession = Depends(get_db_session), songs_img_dir: str = Depends(get_songs_img_dir)):
    """Serve the current room image with strong ETag caching.
    Enforces auth and room access. Supports If-None-Match -> 304.
    """
    room, user_id = room_and_user
    if not room.current_song or not room.current_page:
        raise HTTPException(status_code=404, detail="No current song/page for this room")

    # Deterministic path for current page image
    image_path = os.path.join(songs_img_dir, room.current_song, f"page_{room.current_page}.webp")
    mime = "image/webp"

    # Compute weak ETag based on size and mtime (404 if file unexpectedly missing)
    try:
        st = os.stat(image_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Current page image not available")
    etag_naked = f"{st.st_size:x}-{int(st.st_mtime)}"
    etag_value = f'W/"{etag_naked}"'

    # Conditional GET handling
    if_none_match = request.headers.get('if-none-match')
    if if_none_match:
        # Normalize and compare; support weak or strong token formats
        candidate = if_none_match.strip()
        # Handle multiple ETags (comma-separated)
        etag_candidates = [tag.strip() for tag in candidate.split(',')]
        
        for etag_candidate in etag_candidates:
            normalized_candidate = etag_candidate
            if normalized_candidate.startswith('W/'):
                normalized_candidate = normalized_candidate[2:].strip()
            if normalized_candidate.startswith('"') and normalized_candidate.endswith('"'):
                normalized_candidate = normalized_candidate[1:-1]
            
            if normalized_candidate == etag_naked:
                # 304 Not Modified
                return Response(status_code=304, headers={
                    "ETag": etag_value,
                    "Cache-Control": "private, no-cache",
                })
            
            # Also check for "*" which means any ETag matches
            if etag_candidate.strip() == "*":
                return Response(status_code=304, headers={
                    "ETag": etag_value,
                    "Cache-Control": "private, no-cache",
                })

    headers = {
        "ETag": etag_value,
        "Cache-Control": "private, no-cache",
    }
    return FileResponse(path=image_path, media_type=mime or "application/octet-stream", headers=headers)

# DEPRECATED: /sync endpoint removed - WebSocket provides real-time room state
# Clients should connect via WebSocket after joining a room to receive initial state
# and real-time updates. The WebSocket join_room_success message now includes
# the current room state, eliminating the need for a separate sync call.