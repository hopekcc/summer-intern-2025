import asyncio
import os
import time
import json
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from scripts.runtime.logger import logger as _app_logger
from scripts.runtime.paths import get_songs_pdf_dir, get_songs_img_dir
from scripts.runtime.database import (
    Room, RoomParticipant, User, Song, get_db_session,
    get_room_by_id_from_db, get_song_by_id_from_db,
    create_room_db, delete_room, add_participant, remove_participant,
    generate_room_id, get_room, log_room_action
)
from scripts.runtime.auth_middleware import get_current_user, get_room_access, get_host_access
from scripts.runtime.websocket_server import get_websocket_factory

router = APIRouter(tags=["Rooms"])
logger = _app_logger.getChild("rooms")

# ============================================================================
# REQUEST MODELS
# ============================================================================

class SelectSongRequest(BaseModel):
    song_id: str = Field(..., description="Song ID to select for the room", example="song_123")

class UpdatePageRequest(BaseModel):
    page: int = Field(..., description="Page number to navigate to", example=1, ge=1)

# ============================================================================
# HTTP Endpoints - Room Management
# ============================================================================

# ============================================================================
# ETag Helpers for Image Caching
# ============================================================================

_ETAG_BITS = os.getenv("ETAG_BITS", "128")
try:
    _ETAG_BITS_INT = int(_ETAG_BITS)
    if _ETAG_BITS_INT not in (64, 128, 256):
        _ETAG_BITS_INT = 128
except Exception:
    _ETAG_BITS_INT = 128

_ETAG_CACHE: Dict[Tuple[str, int, int, int], str] = {}

def _blake2b_hexdigest(path: str, digest_bits: int) -> str:
    """Generate BLAKE2b hash for file ETag with caching.
    
    Args:
        path: File path to hash
        digest_bits: Hash digest size in bits (64, 128, or 256)
        
    Returns:
        str: Hexadecimal hash digest
    """
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

@router.post("/", summary="Create Room", description="Create a new room for the authenticated host. Automatically cleans up any existing rooms for the host.")
async def create_room(
    host_data = Depends(get_current_user), 
    session: AsyncSession = Depends(get_db_session)
):
    """Create a new room for the authenticated host.
    
    Automatically cleans up any existing rooms for the host before
    creating the new room to maintain one-room-per-host constraint.
    
    Args:
        host_data: Firebase user data from authentication middleware
        session: Database session
        
    Returns:
        dict: Room creation response with room_id
        
    Raises:
        HTTPException: If room creation fails
    """
    start_time = time.perf_counter()
    host_id = host_data['uid']
    
    try:
        # Clean up existing rooms first
        await _cleanup_existing_host_rooms(session, host_id)
        
        # Create new room
        room_id = await _create_new_room(session, host_id)
        
        # Setup WebSocket registration
        await _setup_websocket_room(room_id)
        
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Room created successfully",
            extra={
                "operation": "create_room",
                "room_id": room_id,
                "host_id": host_id,
                "duration_ms": round(elapsed, 1),
                "status": "success"
            }
        )
        return {"room_id": room_id}
        
    except Exception as e:
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.error(
            "Failed to create room",
            exc_info=True,
            extra={
                "operation": "create_room",
                "host_id": host_id,
                "error": str(e),
                "duration_ms": round(elapsed, 1),
                "status": "failed"
            }
        )
        raise HTTPException(status_code=500, detail="Could not create room.")


async def _cleanup_existing_host_rooms(session: AsyncSession, host_id: str):
    """Clean up any existing rooms for the given host.
    
    Args:
        session: Database session
        host_id: Firebase UID of the host
    """
    cleanup_start = time.perf_counter()
    
    try:
        # Find existing rooms hosted by this user
        existing_rooms_result = await session.execute(
            select(Room).where(Room.host_id == host_id)
        )
        existing_rooms = existing_rooms_result.scalars().all()
        
        if existing_rooms:
            logger.info(
                "Cleaning up existing rooms",
                extra={
                    "operation": "cleanup_existing_rooms",
                    "host_id": host_id,
                    "room_count": len(existing_rooms)
                }
            )
            
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
                        logger.warning(
                            "Failed to notify room closure",
                            exc_info=True,
                            extra={
                                "operation": "cleanup_room_notification",
                                "room_id": old_room.room_id
                            }
                        )
                
                # Delete the room (this also deletes participants via cascade)
                await delete_room(session, old_room)
            
            cleanup_elapsed = (time.perf_counter() - cleanup_start) * 1000
            logger.info(
                "Room cleanup completed",
                extra={
                    "operation": "cleanup_existing_rooms",
                    "host_id": host_id,
                    "room_count": len(existing_rooms),
                    "duration_ms": round(cleanup_elapsed, 1),
                    "status": "success"
                }
            )
            
    except Exception as e:
        cleanup_elapsed = (time.perf_counter() - cleanup_start) * 1000
        logger.warning(
            "Failed to cleanup old rooms",
            exc_info=True,
            extra={
                "operation": "cleanup_existing_rooms",
                "host_id": host_id,
                "error": str(e),
                "duration_ms": round(cleanup_elapsed, 1),
                "status": "failed"
            }
        )
        # Continue with room creation even if cleanup fails


async def _create_new_room(session: AsyncSession, host_id: str) -> str:
    """Create a new room and return the room ID.
    
    Args:
        session: Database session
        host_id: Firebase UID of the host
        
    Returns:
        str: Generated room ID
    """
    room_id = generate_room_id()
    new_room = await create_room_db(session, room_id, host_id)
    await session.commit()
    
    logger.info(
        "New room created in database",
        extra={
            "operation": "create_new_room",
            "room_id": room_id,
            "host_id": host_id
        }
    )
    return room_id


async def _setup_websocket_room(room_id: str):
    """Pre-register room with WebSocket factory.
    
    Args:
        room_id: Room ID to register
    """
    try:
        ws_factory = get_websocket_factory()
        if ws_factory:
            ws_factory.register_room(room_id)
            logger.info(
                "WebSocket room registered",
                extra={
                    "operation": "setup_websocket_room",
                    "room_id": room_id,
                    "status": "success"
                }
            )
    except Exception as e:
        logger.warning(
            "Failed to pre-register WebSocket room",
            exc_info=True,
            extra={
                "operation": "setup_websocket_room",
                "room_id": room_id,
                "error": str(e),
                "status": "failed"
            }
        )

@router.post("/{room_id}/join", response_model=None, summary="Join Room", description="Add a user to an existing room.")
async def join_room(
    room_id: str, 
    room_and_user = Depends(get_room_access), 
    session: AsyncSession = Depends(get_db_session)
):
    """Add a user to an existing room.
    
    Args:
        room_id: ID of the room to join
        room_and_user: Room and user data from access middleware
        session: Database session
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If join operation fails
    """
    start_time = time.perf_counter()
    room, user_id = room_and_user
    
    try:
        db_start = time.perf_counter()
        await add_participant(session, room_id, user_id)
        await session.commit()
        db_elapsed = (time.perf_counter() - db_start) * 1000
        
        logger.info(
            "Participant added to database",
            extra={
                "operation": "add_participant",
                "room_id": room_id,
                "user_id": user_id,
                "duration_ms": round(db_elapsed, 1)
            }
        )
        
        # Notify room participants via WebSocket
        ws_factory = get_websocket_factory()
        if ws_factory:
            try:
                ws_factory.register_room(room_id)
                asyncio.create_task(ws_factory.broadcast_to_room(room_id, {
                    "type": "participant_joined",
                    "user_id": user_id
                }))
                logger.info(
                    "Participant joined notification sent",
                    extra={
                        "operation": "join_room_notification",
                        "room_id": room_id,
                        "user_id": user_id,
                        "status": "success"
                    }
                )
            except Exception as e:
                logger.warning(
                    "Failed to register room or send notification",
                    exc_info=True,
                    extra={
                        "operation": "join_room_notification",
                        "room_id": room_id,
                        "user_id": user_id,
                        "error": str(e),
                        "status": "failed"
                    }
                )
        else:
            logger.warning(
                "WebSocket factory not available",
                extra={
                    "operation": "join_room_notification",
                    "room_id": room_id,
                    "user_id": user_id,
                    "status": "no_websocket"
                }
            )
        
        total_elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(
            "User joined room successfully",
            extra={
                "operation": "join_room",
                "room_id": room_id,
                "user_id": user_id,
                "duration_ms": round(total_elapsed, 1),
                "status": "success"
            }
        )
        return {"message": f"User {user_id} joined room {room_id}"}
    except HTTPException as e:
        raise e
    except Exception as e:
        total_elapsed = (time.perf_counter() - start_time) * 1000
        logger.error(
            "Failed to join room",
            exc_info=True,
            extra={
                "operation": "join_room",
                "room_id": room_id,
                "user_id": user_id,
                "error": str(e),
                "duration_ms": round(total_elapsed, 1),
                "status": "failed"
            }
        )
        raise HTTPException(status_code=500, detail="Could not join room.")

@router.post("/{room_id}/leave", response_model=None, summary="Leave Room", description="Remove a user from a room. If host leaves, room is closed.")
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

@router.get("/{room_id}", response_model=None, summary="Get Room Details", description="Retrieve room information including participants and current song.")
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

@router.post("/{room_id}/song", response_model=None, summary="Select Song", description="Select a song for the room. Only the host can perform this action.")
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

@router.post("/{room_id}/page", response_model=None, summary="Update Page", description="Navigate to a specific page of the current song. Only the host can perform this action.")
async def update_room_page(room_id: str, request: UpdatePageRequest, host_data = Depends(get_host_access), session: AsyncSession = Depends(get_db_session), songs_img_dir: str = Depends(get_songs_img_dir)):
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

        # Check page bounds against current song
        if current_room.current_song:
            song = await get_song_by_id_from_db(session, current_room.current_song)
            if song and page > getattr(song, 'page_count', 1):
                raise HTTPException(status_code=400, detail={
                    "code": "PAGE_OUT_OF_RANGE",
                    "message": f"Page {page} is out of range. Song has {getattr(song, 'page_count', 1)} pages."
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
                # Load song details for the current song
                song = await get_song_by_id_from_db(session, current_room.current_song)
                if song is None:
                    raise HTTPException(status_code=404, detail=f"Song with ID '{current_room.current_song}' not found")
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

@router.get("/{room_id}/pdf", summary="Download PDF", description="Download the PDF file of the current song in the room.")
async def download_room_pdf(room_id: str, request: Request, room_and_user = Depends(get_room_access), session: AsyncSession = Depends(get_db_session)):
    try:
        room, user_id = room_and_user
        if not room.current_song:
            raise HTTPException(status_code=404, detail="No current song in this room")

        # Get song details from the songs database
        song = await get_song_by_id_from_db(session, room.current_song)
        if song is None:
            raise HTTPException(status_code=404, detail=f"Song with ID '{room.current_song}' not found")
        
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

@router.get("/{room_id}/image", summary="Get Song Image", description="Get the current page image of the song being displayed in the room.")
async def get_room_current_image(
    room_id: str,
    request: Request,
    room_and_user = Depends(get_room_access),
    session: AsyncSession = Depends(get_db_session),
    songs_img_dir: str = Depends(get_songs_img_dir),
):
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