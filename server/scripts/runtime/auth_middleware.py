"""
Centralized authentication middleware for both HTTP and WebSocket routes.
Provides consistent token verification and role-based access control.
"""
import json
from typing import Optional, Dict, List, Set, Tuple, Callable, Any, Union

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from firebase_admin.auth import InvalidIdTokenError
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from scripts.runtime.database import Room, get_db_session
from scripts.runtime.logger import logger

# Shared security object (same as in dependencies.py for backward compatibility)
security = HTTPBearer()

# Standardized error messages
AUTH_ERRORS = {
    "missing_token": "Authentication required",
    "invalid_token": "Invalid authentication token",
    "expired_token": "Authentication token has expired",
    "forbidden": "You don't have permission to perform this action",
    "room_not_found": "Room not found",
    "not_host": "Only the room host can perform this action"
}

# =====================================
# Core Token Verification
# =====================================

async def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify a Firebase token and return decoded claims.
    Centralizes token verification and error handling.
    
    Args:
        token: Firebase ID token
        
    Returns:
        dict: Decoded token with user claims
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        return auth.verify_id_token(token)
    except InvalidIdTokenError as e:
        if "expired" in str(e).lower():
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, 
                detail=AUTH_ERRORS["expired_token"]
            )
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, 
            detail=AUTH_ERRORS["invalid_token"]
        )
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, 
            detail=f"Authentication failed: {str(e)}"
        )

# =====================================
# FastAPI Dependencies
# =====================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency that extracts and verifies the user token.
    Direct replacement for the original verify_firebase_token function.
    
    Args:
        credentials: HTTP Authorization header with Bearer token
        
    Returns:
        dict: Decoded user data from token
    """
    return await verify_token(credentials.credentials)

async def get_room_by_id(
    room_id: str,
    session: AsyncSession
) -> Room:
    """
    Get a room by ID or raise a 404 exception.
    
    Args:
        room_id: Room identifier
        session: Database session
        
    Returns:
        Room: The requested room
        
    Raises:
        HTTPException: If room not found
    """
    # Import here to avoid circular imports
    from scripts.runtime.database import get_room_by_id_from_db as get_room
    
    room = await get_room(session, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=AUTH_ERRORS["room_not_found"]
        )
    return room

# Import session dependencies from the dedicated module


async def get_room_access(
    room_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> Tuple[Room, str]:
    """
    Verify a user has basic access to a room.
    Returns both the room and the user ID for convenience.
    
    Args:
        room_id: Room identifier
        user: Authenticated user info from token
        session: Database session
        
    Returns:
        tuple: (Room object, User ID)
    """
    user_id = user['uid']
    room = await get_room_by_id(room_id, session)
    # Note: Currently all authenticated users can access rooms
    # This is where additional access checks could be added in the future
    return room, user_id

async def verify_room_host(
    room: Room, 
    user_id: str
) -> None:
    """
    Verify the user is the host of the room.
    
    Args:
        room: Room object
        user_id: User ID to check
        
    Raises:
        HTTPException: If user is not host
    """
    if room.host_id != user_id:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=AUTH_ERRORS["not_host"]
        )

async def get_host_access(
    room_and_user = Depends(get_room_access)
) -> Tuple[Room, str]:
    """
    Verify a user is the host of a room.
    Returns both the room and user ID for convenience.
    
    Args:
        room_and_user: Tuple from get_room_access
        
    Returns:
        tuple: (Room object, User ID)
        
    Raises:
        HTTPException: If user is not the host
    """
    room, user_id = room_and_user
    await verify_room_host(room, user_id)
    return room, user_id

# =====================================
# WebSocket Authentication
# =====================================

async def authenticate_websocket(
    token: str
) -> Union[Dict[str, Any], Dict[str, str]]:
    """
    Authenticate a WebSocket connection using Firebase token.
    Returns user data on success or error details on failure.
    
    Args:
        token: Firebase ID token
        
    Returns:
        dict: Either user data or error information
    """
    try:
        return await verify_token(token)
    except HTTPException as e:
        # Convert HTTP exception to WebSocket-friendly format
        return {"error": e.detail, "status": e.status_code}

# =====================================
# Backward Compatibility Layer
# =====================================

# Legacy compatibility - use get_current_user instead
verify_firebase_token = get_current_user
