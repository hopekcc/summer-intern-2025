import logging
from typing import Tuple, Optional
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from scripts.runtime.database import get_db_session, get_db_session as get_song_async_session
from scripts.runtime.paths import (
    get_database_dir, get_songs_dir, get_songs_pdf_dir, 
    get_metadata_path, get_songs_img_dir
)

# Import centralized auth middleware
from scripts.runtime.auth_middleware import (
    get_current_user, get_room_access, get_host_access, 
    verify_firebase_token
)

# Database Session Dependencies are now imported from scripts.runtime.database

# Path dependencies are now imported from scripts.runtime.paths