import os
import gzip
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from scripts.runtime.logger import logger as _app_logger

# Import from our consolidated modules
from scripts.runtime.paths import get_songs_pdf_dir, get_songs_img_dir, get_songs_list_gzip_path
from scripts.runtime.database import (
    Song,
    get_db_session,
    search_songs,
    get_song_by_id_from_db,
    search_songs_substring,
    search_songs_similarity,
    search_songs_text,
)
from scripts.runtime.auth_middleware import get_current_user

logger = _app_logger.getChild("api.songs")

router = APIRouter()

# ============================================================================
# SONG MANAGEMENT HELPERS
# ============================================================================

# Note: song DB helpers are imported from `scripts.runtime.database`

async def get_song_dependency(song_id: str, db: AsyncSession = Depends(get_db_session)) -> Song:
    """Dependency to get a song by its ID from the database asynchronously."""
    song = await get_song_by_id_from_db(db, song_id)
    if song is None:
        raise HTTPException(status_code=404, detail=f"Song with ID '{song_id}' not found")
    return song

async def songPDFHelper(
    song_id: str,
    db: AsyncSession = Depends(get_db_session),
    songs_pdf_dir: str = Depends(get_songs_pdf_dir)
):
    song = await get_song_by_id_from_db(db, song_id)
    if song is None:
        raise HTTPException(status_code=404, detail=f"Song with ID '{song_id}' not found")
    # Prefer new layout: songs_pdf/{id}.pdf
    pdf_filename = f"{song.id}.pdf"
    pdf_path = os.path.join(songs_pdf_dir, pdf_filename)
    if os.path.exists(pdf_path):
        return pdf_path
    # Back-compat fallback: songs_pdf/{basename(filename)}.pdf
    if song.filename:
        legacy_name = f"{os.path.splitext(song.filename)[0]}.pdf"
        legacy_path = os.path.join(songs_pdf_dir, legacy_name)
        if os.path.exists(legacy_path):
            return legacy_path
    # Not found
    raise HTTPException(status_code=404, detail="PDF file not found.")

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", response_model=None)
async def get_songs_list(
    search: str = None,
    limit: int = 50,
    offset: int = 0,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Get songs with pagination and optional search. Accessible via /songs/ and /songs/list"""
    try:
        if search:
            # Search with limit
            songs = await search_songs(session, search, limit)
        else:
            # Get paginated results instead of all songs
            query = select(Song).order_by(Song.title).offset(offset).limit(limit)
            result = await session.execute(query)
            songs = result.scalars().all()
        
        return songs
    except Exception as e:
        logger.error(f"Failed to retrieve songs: {str(e)}", exc_info=True)
        return []

@router.get("/list", response_model=None)
def get_songs_list_json(
    current_user=Depends(get_current_user),
    gz_path: str = Depends(get_songs_list_gzip_path)
):
    """Return the full songs list as JSON by decoding the pre-generated gzip file.

    Temporarily returns plain JSON (not gzip) to simplify clients.
    """
    if not os.path.exists(gz_path):
        raise HTTPException(status_code=404, detail="Songs list not available. Run ingestion sync.")

    try:
        st = os.stat(gz_path)
        with gzip.open(gz_path, 'rb') as f:
            raw = f.read()
        text = raw.decode('utf-8')
        try:
            data = json.loads(text)
            # Some generators accidentally dump JSON twice; handle nested string
            if isinstance(data, str):
                data = json.loads(data)
        except Exception:
            # Fallback: return text as-is inside an object
            data = {"raw": text}
        # FastAPI will serialize this as JSON automatically
        return data
    except Exception as e:
        logger.error(f"Failed to decode songs list gzip: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to read songs list")

@router.get("/{song_id}", response_model=None)
async def get_specific_song(
    current_user=Depends(get_current_user),
    song: Song = Depends(get_song_dependency),
    songs_pdf_dir: str = Depends(get_songs_pdf_dir)
):
    # Convert to dict so we can add additional fields
    song_dict = song.model_dump()
    
    # Add the total pages information
    # Prefer new layout by song ID, then fallback to legacy filename-based PDF
    pdf_filename = f"{song.id}.pdf"
    pdf_path = os.path.join(songs_pdf_dir, pdf_filename)
    if not os.path.exists(pdf_path) and song.filename:
        legacy_name = f"{os.path.splitext(song.filename)[0]}.pdf"
        legacy_path = os.path.join(songs_pdf_dir, legacy_name)
        if os.path.exists(legacy_path):
            pdf_path = legacy_path
    
    # Add PDF information
    if os.path.exists(pdf_path):
        song_dict["pdf_url"] = f"/songs/{song.id}/pdf"
        song_dict["total_pages"] = song.page_count
    else:
        song_dict["pdf_url"] = None
        song_dict["total_pages"] = 0
        
    # Add image URL (for cover/thumbnail)
    song_dict["image_url"] = f"/songs/{song.id}/image"
    
    return song_dict

@router.get("/{song_id}/pdf")
async def get_song_pdf(
    song_id: str, 
    current_user=Depends(get_current_user),
    pdf_path: str = Depends(songPDFHelper)
):
    st = os.stat(pdf_path)
    headers = {
        "Cache-Control": "public, max-age=86400",
        "ETag": f"W/\"{st.st_size:x}-{int(st.st_mtime)}\"",
    }
    return FileResponse(
        path=pdf_path,
        filename=os.path.basename(pdf_path),
        media_type="application/pdf",
        headers=headers,
    )
    
@router.get("/{song_id}/image")
def get_song_image(
    song_id: str,
    current_user=Depends(get_current_user),
    song: Song = Depends(get_song_dependency),
    songs_img_dir: str = Depends(get_songs_img_dir)
):
    """Return the song image from the songs_img directory"""
    # Deterministic layout: songs_img/{song_id}/page_1.webp (cover thumbnail)
    # DB-backed guard: ensure the song has at least one page
    if getattr(song, "page_count", 0) < 1:
        raise HTTPException(status_code=404, detail="Song has no pages")
    song_dir = os.path.join(songs_img_dir, song.id)
    path = os.path.join(song_dir, "page_1.webp")
    try:
        st = os.stat(path)
    except FileNotFoundError:
        # Unexpected if retriever guarantees assets, but fail fast with 404
        raise HTTPException(status_code=404, detail="Song image not available")
    headers = {
        "Cache-Control": "public, max-age=86400",
        "ETag": f"W/\"{st.st_size:x}-{int(st.st_mtime)}\"",
    }
    return FileResponse(path=path, media_type="image/webp", headers=headers)

@router.get("/{song_id}/page/{page_number}")
def get_song_page_image(
    song_id: str,
    page_number: int,
    current_user=Depends(get_current_user),
    song: Song = Depends(get_song_dependency),
    songs_img_dir: str = Depends(get_songs_img_dir)
):
    """Return a specific page image for a song from the songs_img directory"""
    # Deterministic layout: songs_img/{song_id}/page_{n}.webp
    # DB-backed guard: page bounds check to avoid unnecessary FS work
    if page_number < 1 or page_number > getattr(song, "page_count", 0):
        raise HTTPException(status_code=404, detail=f"Page {page_number} is out of range (1..{song.page_count}) for song {song_id}")
    song_dir = os.path.join(songs_img_dir, song.id)
    path = os.path.join(song_dir, f"page_{page_number}.webp")
    try:
        st = os.stat(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Page {page_number} image not available for song {song_id}")
    headers = {
        "Cache-Control": "public, max-age=86400",
        "ETag": f"W/\"{st.st_size:x}-{int(st.st_mtime)}\"",
    }
    return FileResponse(path=path, media_type="image/webp", headers=headers)

@router.get("/search/substring", response_model=None)
async def search_substring(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=100),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Case-insensitive substring search on title and artist with tiered scoring."""
    return await search_songs_substring(session, q, limit)


@router.get("/search/similarity", response_model=None)
async def search_similarity(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=100),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Trigram similarity search (pg_trgm)."""
    return await search_songs_similarity(session, q, limit)


@router.get("/search/text", response_model=None)
async def search_text(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=100),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Full-text search on title+artist with normalized ts_rank scoring."""
    return await search_songs_text(session, q, limit)