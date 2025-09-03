"""
Unified Database Access Layer
This completely replaces database_models.py and song_database_models.py
Simplified to a single env-configured async engine with one session factory.
"""
from typing import Optional, List, AsyncGenerator, Tuple
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert as pg_insert

import os
import time
import asyncio
import uuid
from scripts.runtime.logger import logger as _app_logger
logger = _app_logger.getChild("db")

def get_database_url() -> str:
    """Read DATABASE_URL from env and enforce PostgreSQL (asyncpg)."""
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL must be set and use postgresql+asyncpg (PostgreSQL-only)."
        )
    if not (url.startswith("postgresql+asyncpg://") or url.startswith("postgresql+asyncpg:")):
        raise RuntimeError(
            "Unsupported DATABASE_URL. This project is PostgreSQL-only. Use postgresql+asyncpg://USER:PASS@HOST:PORT/DBNAME"
        )
    return url

# --- Pool/env helpers ---
def _parse_bool(val: str, default: bool = False) -> bool:
    if val is None:
        return default
    s = str(val).strip().lower()
    return s in {"1", "true", "yes", "on", "y", "t"}

def _parse_int(val: str, default: int) -> int:
    try:
        return int(str(val).strip()) if val is not None else default
    except Exception:
        return default

# Models
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    firebase_uid: str = Field(unique=True, index=True)
    display_name: Optional[str] = None
    email: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Remove room relationships since host_id is now string

class Song(SQLModel, table=True):
    __tablename__ = "songs"
    
    id: str = Field(primary_key=True)
    title: str = Field(index=True)
    artist: Optional[str] = Field(default=None, index=True)
    genre: Optional[str] = Field(default=None, index=True)
    key: Optional[str] = None
    tempo: Optional[str] = None
    language: Optional[str] = Field(default="English")
    date_added: datetime = Field(default_factory=datetime.utcnow)
    filename: Optional[str] = None
    page_count: int

    # Add relationship back to PlaylistSong
    playlist_songs: List["PlaylistSong"] = Relationship(back_populates="song")


class Room(SQLModel, table=True):
    __tablename__ = "room"  # Match original schema
    
    room_id: str = Field(primary_key=True, index=True)  # Add index for performance
    host_id: str = Field(index=True)  # Add index for host lookups
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Song fields - NO foreign key constraint for performance
    current_song: Optional[str] = None
    current_page: Optional[int] = None
    current_song_id: Optional[str] = Field(default=None, index=True)  # Just indexed string, no FK
    
    # Relationships - participants only, no song relationship
    participants: List["RoomParticipant"] = Relationship(back_populates="room")

class RoomParticipant(SQLModel, table=True):
    __tablename__ = "roomparticipant"  # Match original schema
    
    room_id: str = Field(foreign_key="room.room_id", primary_key=True, index=True)  # Add index
    user_id: str = Field(primary_key=True, index=True)  # Changed to str to match Firebase UIDs
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    
    room: Room = Relationship(back_populates="participants")

# Duplicate imports removed - using main imports above


class Playlist(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    description: Optional[str] = None
    user_id: str = Field(index=True)  # Firebase UID as indexed string (no FK constraint)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    songs: List["PlaylistSong"] = Relationship(back_populates="playlist")

class PlaylistSong(SQLModel, table=True):
    playlist_id: str = Field(foreign_key="playlist.id", primary_key=True)
    song_id: str = Field(foreign_key="songs.id", primary_key=True)
    added_at: datetime = Field(default_factory=datetime.utcnow)
    position: int = Field(default=0)  # For future ordering support
    playlist: Playlist = Relationship(back_populates="songs")
    song: Song = Relationship(back_populates="playlist_songs")

# Single async engine configured by env (PostgreSQL-only)
# DATABASE_URL will be set when get_engine() is called

# Determine environment (dev/prod-style defaults)
IS_PROD = _parse_bool(os.getenv("PROD", "0"), default=False)

# Defaults differ for dev vs prod; env can override
default_pool_size = 8 if IS_PROD else 5
default_max_overflow = 4 if IS_PROD else 5
default_timeout = 30
default_recycle = 1800
default_pre_ping = True if IS_PROD else False
default_use_lifo = True
default_stmt_cache = 1000 if IS_PROD else 500

POOL_SIZE = _parse_int(os.getenv("DB_POOL_SIZE"), default_pool_size)
MAX_OVERFLOW = _parse_int(os.getenv("DB_MAX_OVERFLOW"), default_max_overflow)
POOL_TIMEOUT = _parse_int(os.getenv("DB_POOL_TIMEOUT"), default_timeout)
POOL_RECYCLE = _parse_int(os.getenv("DB_POOL_RECYCLE"), default_recycle)
POOL_PRE_PING = _parse_bool(os.getenv("DB_PRE_PING"), default_pre_ping)
POOL_USE_LIFO = _parse_bool(os.getenv("DB_POOL_USE_LIFO"), default_use_lifo)
STMT_CACHE_SIZE = _parse_int(os.getenv("DB_STMT_CACHE_SIZE"), default_stmt_cache)

engine_kwargs = {
    "echo": bool(int(os.getenv("DB_ECHO", "0"))),
    "pool_size": POOL_SIZE,
    "max_overflow": MAX_OVERFLOW,
    "pool_timeout": POOL_TIMEOUT,
    "pool_recycle": POOL_RECYCLE,
    "pool_pre_ping": POOL_PRE_PING,
    "pool_use_lifo": POOL_USE_LIFO,
    # asyncpg prepared statement cache per connection
    "connect_args": {"statement_cache_size": STMT_CACHE_SIZE},
}

# Log effective pool config once on startup
logger.info(
    "db_pool_config",
    extra={
        "pool_size": POOL_SIZE,
        "max_overflow": MAX_OVERFLOW,
        "pool_timeout": POOL_TIMEOUT,
        "pool_recycle": POOL_RECYCLE,
        "pre_ping": POOL_PRE_PING,
        "use_lifo": POOL_USE_LIFO,
        "stmt_cache_size": STMT_CACHE_SIZE,
        "prod": IS_PROD,
    },
)

# Engine will be created lazily when needed
engine = None
AsyncSessionLocal = None

def get_engine():
    """Get or create the database engine"""
    global engine, AsyncSessionLocal
    if engine is None:
        DATABASE_URL = get_database_url()
        engine = create_async_engine(DATABASE_URL, **engine_kwargs)
        AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False)
    return engine

def get_session_factory():
    """Get the session factory, ensuring engine is initialized"""
    get_engine()  # This will initialize both engine and AsyncSessionLocal
    return AsyncSessionLocal

# Database creation functions
async def create_db_and_tables_async():
    """Create database and all tables (asynchronous)"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.commit()

# Session management
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield a single async session."""
    get_engine()  # Ensure engine is initialized
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def normalize_song_id(song_id: str) -> str:
    """Normalize song ID by removing leading zeros from numeric IDs."""
    if isinstance(song_id, str) and song_id.isdigit():
        try:
            # Convert to int and back to string to remove leading zeros
            return str(int(song_id))
        except ValueError:
            pass
    return song_id

# Core database functions
async def get_song_by_id_from_db(session: AsyncSession, song_id: str) -> Optional[Song]:
    """Get song by ID using the provided session with smart fallback for different ID formats"""
    start_time = time.perf_counter()
    
    # Normalize the input ID first
    normalized_id = normalize_song_id(song_id)
    
    # Try normalized ID first
    result = await session.execute(select(Song).where(Song.id == normalized_id))
    song = result.scalars().first()
    
    # If not found and input was different from normalized, try original
    if not song and normalized_id != song_id:
        result = await session.execute(select(Song).where(Song.id == song_id))
        song = result.scalars().first()
    
    # Fallback: try common padding formats for numeric IDs
    if not song and isinstance(song_id, str) and song_id.isdigit():
        try:
            numeric_val = int(song_id)
            # Try 4-digit padded format (legacy)
            padded4 = f"{numeric_val:04d}"
            if padded4 != song_id and padded4 != normalized_id:
                result = await session.execute(select(Song).where(Song.id == padded4))
                song = result.scalars().first()
        except Exception:
            # If any conversion error occurs, ignore and proceed with song as None
            pass

    elapsed = (time.perf_counter() - start_time) * 1000
    logger.info(f"get_song_by_id_from_db", extra={"duration_ms": round(elapsed, 1), "ws_event": "db_song_lookup", "status_code": 200, "page": getattr(song, 'page_count', None)})
    return song

async def get_room_by_id_from_db(session: AsyncSession, room_id: str) -> Optional[Room]:
    # Get room by ID with performance logging
    start_time = time.perf_counter()
    result = await session.execute(select(Room).where(Room.room_id == room_id))
    room = result.scalars().first()
    elapsed = (time.perf_counter() - start_time) * 1000
    logger.info("get_room_by_id_from_db", extra={"duration_ms": round(elapsed, 1), "ws_event": "db_room_lookup"})
    return room

# Search functions
async def search_songs(session: AsyncSession, query: str, limit: int = 50) -> List[Song]:
    """Search songs by title or artist using case-insensitive matching (ILIKE).

    This is the fast, DB-native baseline. It avoids Python-side fuzzy matching.
    For better ranking on large datasets, add pg_trgm indexes and switch to
    similarity-based ordering in a future step.
    """
    q = (query or "").strip()
    if not q:
        return []
    pattern = f"%{q}%"
    stmt = (
        select(Song)
        .where((Song.title.ilike(pattern)) | (Song.artist.ilike(pattern)))
        .order_by(Song.title)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def search_songs_substring(session: AsyncSession, query: str, limit: int = 10) -> List[dict]:
    """Substring search on `title` and `artist` with simple tiered scoring.

    Scoring (max of title/artist match):
    - exact = 100
    - prefix = 85
    - contains = 70
    Returns a list of dicts with song_id, title, artist, page_count, score, score_type.
    """
    q = (query or "").strip()
    if not q:
        return []
    pattern = f"%{q}%"
    stmt = (
        select(Song)
        .where((Song.title.ilike(pattern)) | (Song.artist.ilike(pattern)))
        .limit(max(5 * limit, limit))
    )
    result = await session.execute(stmt)
    songs = result.scalars().all()

    q_lower = q.lower()
    def score_field(val: Optional[str]) -> int:
        if not val:
            return 0
        s = val.lower()
        if s == q_lower:
            return 100
        if s.startswith(q_lower):
            return 85
        if q_lower in s:
            return 70
        return 0

    items = []
    for s in songs:
        sc = max(score_field(s.title), score_field(s.artist))
        if sc <= 0:
            continue
        items.append({
            "song_id": s.id,
            "title": s.title,
            "artist": s.artist,
            "page_count": s.page_count,
            "score": sc,
            "score_type": "substring",
        })
    # Order by score desc then title asc for stability
    items.sort(key=lambda x: (-x["score"], (x["title"] or "")))
    return items[:limit]


async def search_songs_similarity(session: AsyncSession, query: str, limit: int = 10) -> List[dict]:
    """Similarity search using pg_trgm extension."""
    try:
        # Try pg_trgm similarity search first
        sql = """
        SELECT id, title, artist, page_count,
               GREATEST(
                   similarity(title, :query),
                   similarity(COALESCE(artist, ''), :query)
               ) as score
        FROM songs 
        WHERE title % :query OR COALESCE(artist, '') % :query
        ORDER BY score DESC
        LIMIT :limit
        """
        result = await session.execute(text(sql), {"query": query, "limit": limit})
        rows = result.fetchall()
        
        if rows:
            return [
                {
                    "song_id": row.id,
                    "title": row.title,
                    "artist": row.artist,
                    "page_count": row.page_count,
                    "score": round(row.score * 100, 1),
                    "score_type": "similarity",
                }
                for row in rows
            ]
    except Exception as e:
        logger.warning(f"pg_trgm similarity search failed: {e}")
    
    # Fallback to basic search
    songs = await search_songs(session, query, limit)
    return [
        {
            "song_id": song.id,
            "title": song.title,
            "artist": song.artist,
            "page_count": song.page_count,
            "score": 80.0,
            "score_type": "similarity_fallback",
        }
        for song in songs
    ]

async def search_songs_text(session: AsyncSession, query: str, limit: int = 10) -> List[dict]:
    """Full-text search using tsvector column."""
    try:
        # Try tsvector full-text search first
        sql = """
        SELECT id, title, artist, page_count,
               ts_rank(ts, plainto_tsquery('simple', :query)) as score
        FROM songs 
        WHERE ts @@ plainto_tsquery('simple', :query)
        ORDER BY score DESC
        LIMIT :limit
        """
        result = await session.execute(text(sql), {"query": query, "limit": limit})
        rows = result.fetchall()
        
        if rows:
            return [
                {
                    "song_id": row.id,
                    "title": row.title,
                    "artist": row.artist,
                    "page_count": row.page_count,
                    "score": round(row.score * 100, 1),
                    "score_type": "text",
                }
                for row in rows
            ]
    except Exception as e:
        logger.warning(f"tsvector full-text search failed: {e}")
    
    # Fallback to basic search
    songs = await search_songs(session, query, limit)
    return [
        {
            "song_id": song.id,
            "title": song.title,
            "artist": song.artist,
            "page_count": song.page_count,
            "score": 75.0,
            "score_type": "text_fallback",
        }
        for song in songs
    ]


# Helper functions from database_helpers.py
async def create_room_db(session: AsyncSession, room_id: str, host_id: str):
    """Create a new room in the database - caller handles commit"""
    start_time = time.perf_counter()
    room = Room(
        room_id=room_id,
        host_id=host_id
    )
    session.add(room)
    # Don't commit here - let caller batch operations
    elapsed = (time.perf_counter() - start_time) * 1000
    logger.info("create_room_db", extra={"duration_ms": round(elapsed, 1)})
    return room

async def delete_room(session: AsyncSession, room: Room):
    """Delete a room and its participants - caller handles commit"""
    start_time = time.perf_counter()
    # Delete participants in bulk
    await session.execute(
        delete(RoomParticipant).where(RoomParticipant.room_id == room.room_id)
    )
    
    # Delete the room (no commit here)
    await session.delete(room)
    elapsed = (time.perf_counter() - start_time) * 1000
    logger.info("delete_room", extra={"duration_ms": round(elapsed, 1)})

async def add_participant(session: AsyncSession, room_id: str, user_id: str):
    """Add a participant to a room - caller handles commit"""
    # Single round-trip: insert and ignore if already exists
    start_time = time.perf_counter()
    stmt = (
        pg_insert(RoomParticipant.__table__)
        .values(room_id=room_id, user_id=user_id)
        .on_conflict_do_nothing(index_elements=["room_id", "user_id"])
    )
    res = await session.execute(stmt)
    inserted = (res.rowcount or 0) > 0
    elapsed = (time.perf_counter() - start_time) * 1000
    logger.info("add_participant", extra={"duration_ms": round(elapsed, 1), "inserted": inserted})

async def remove_participant(session: AsyncSession, room_id: str, user_id: str):
    """Remove a participant from a room - caller handles commit"""
    start_time = time.perf_counter()
    # Delete directly without fetching first
    res = await session.execute(
        delete(RoomParticipant).where(
            RoomParticipant.room_id == room_id,
            RoomParticipant.user_id == user_id
        )
    )
    # Don't commit here - let caller batch operations
    elapsed = (time.perf_counter() - start_time) * 1000
    deleted = int(res.rowcount or 0)
    logger.info("remove_participant", extra={"duration_ms": round(elapsed, 1), "deleted_count": deleted})

def generate_room_id() -> str:
    """Generate a random room ID"""
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

async def get_room(session: AsyncSession, room_id: str) -> Optional[Room]:
    """Get a room by ID"""
    result = await session.execute(select(Room).where(Room.room_id == room_id))
    return result.scalars().first()

async def log_room_action(session: AsyncSession, room_id: str, action: str, user_id: str, data: dict = None):
    """Log room action - placeholder for now"""
    # TODO: Implement room action logging if needed
    pass


async def check_db_connectivity(timeout_seconds: float = 2.0) -> Tuple[bool, str, float]:
    """Perform a simple async connectivity check: SELECT 1.
    Returns (ok, detail, duration_ms).
    """
    start = time.perf_counter()
    try:
        async with engine.connect() as conn:
            # Use a simple SELECT 1 with timeout
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=timeout_seconds)
        dur_ms = (time.perf_counter() - start) * 1000
        logger.debug("DB healthcheck ok", extra={"duration_ms": round(dur_ms, 1)})
        return True, "ok", dur_ms
    except Exception as e:
        dur_ms = (time.perf_counter() - start) * 1000
        logger.warning("DB healthcheck failed", extra={"error": str(e), "duration_ms": round(dur_ms, 1)})
        return False, str(e), dur_ms

