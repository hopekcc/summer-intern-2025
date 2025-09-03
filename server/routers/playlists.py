from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from scripts.runtime.database import Playlist, PlaylistSong, Song, get_db_session
from scripts.runtime.auth_middleware import get_current_user

router = APIRouter()

# Request Models
class CreatePlaylistRequest(BaseModel):
    name: str
    description: Optional[str] = None

class AddSongRequest(BaseModel):
    song_id: str

class AddMultipleSongsRequest(BaseModel):
    song_ids: List[str]

# Helper function to validate playlist ownership
async def get_user_playlist(playlist_id: str, user_id: str, session: AsyncSession) -> Optional[Playlist]:
    """Get playlist if it belongs to the user."""
    query = select(Playlist).where(Playlist.id == playlist_id, Playlist.user_id == user_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@router.post("/")
async def create_playlist(
    request: CreatePlaylistRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Create a new playlist."""
    user_id = current_user["uid"]
    playlist = Playlist(
        name=request.name, 
        user_id=user_id,
        description=request.description
    )
    session.add(playlist)
    await session.commit()
    await session.refresh(playlist)
    
    return {
        "success": True,
        "data": {
            "id": playlist.id,
            "name": playlist.name,
            "description": playlist.description,
            "user_id": playlist.user_id
        },
        "message": "Playlist created successfully"
    }

@router.post("/{playlist_id}/songs")
async def add_song_to_playlist(
    playlist_id: str,
    request: AddSongRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Add a song to a playlist."""
    user_id = current_user["uid"]
    
    # Validate playlist ownership
    playlist = await get_user_playlist(playlist_id, user_id, session)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found or access denied")
    
    # Validate song exists
    song_query = select(Song).where(Song.id == request.song_id)
    song_result = await session.execute(song_query)
    song = song_result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    # Check if song already in playlist
    existing_query = select(PlaylistSong).where(
        PlaylistSong.playlist_id == playlist_id,
        PlaylistSong.song_id == request.song_id
    )
    existing_result = await session.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Song already in playlist")
    
    playlist_song = PlaylistSong(playlist_id=playlist_id, song_id=request.song_id)
    session.add(playlist_song)
    await session.commit()
    
    return {
        "success": True,
        "data": {
            "playlist_id": playlist_id,
            "song_id": request.song_id,
            "song_title": song.title
        },
        "message": f"Song '{song.title}' added to playlist '{playlist.name}'"
    }

@router.post("/{playlist_id}/songs/bulk")
async def add_multiple_songs_to_playlist(
    playlist_id: str,
    request: AddMultipleSongsRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Add multiple songs to a playlist."""
    user_id = current_user["uid"]
    
    # Validate playlist ownership
    playlist = await get_user_playlist(playlist_id, user_id, session)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found or access denied")
    
    added_songs = []
    skipped_songs = []
    
    for song_id in request.song_ids:
        # Validate song exists
        song_query = select(Song).where(Song.id == song_id)
        song_result = await session.execute(song_query)
        song = song_result.scalar_one_or_none()
        if not song:
            skipped_songs.append({"song_id": song_id, "reason": "Song not found"})
            continue
        
        # Check if song already in playlist
        existing_query = select(PlaylistSong).where(
            PlaylistSong.playlist_id == playlist_id,
            PlaylistSong.song_id == song_id
        )
        existing_result = await session.execute(existing_query)
        if existing_result.scalar_one_or_none():
            skipped_songs.append({"song_id": song_id, "reason": "Already in playlist"})
            continue
        
        playlist_song = PlaylistSong(playlist_id=playlist_id, song_id=song_id)
        session.add(playlist_song)
        added_songs.append({"song_id": song_id, "title": song.title})
    
    await session.commit()
    
    return {
        "success": True,
        "data": {
            "playlist_id": playlist_id,
            "added_songs": added_songs,
            "skipped_songs": skipped_songs
        },
        "message": f"Added {len(added_songs)} songs to playlist '{playlist.name}'"
    }

@router.get("/")
async def get_playlists(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user's playlists with their songs."""
    user_id = current_user["uid"]
    
    query = select(Playlist).where(Playlist.user_id == user_id)
    result = await session.execute(query)
    playlists = result.scalars().all()

    playlists_with_songs = []
    for playlist in playlists:
        # Fetch songs for each playlist
        song_query = select(PlaylistSong, Song).join(Song, PlaylistSong.song_id == Song.id).where(
            PlaylistSong.playlist_id == playlist.id
        )
        song_result = await session.execute(song_query)
        songs = song_result.all()

        # Format the playlist with its songs
        playlists_with_songs.append({
            "id": playlist.id,
            "name": playlist.name,
            "description": playlist.description,
            "user_id": playlist.user_id,
            "song_count": len(songs),
            "songs": [{"id": song.Song.id, "title": song.Song.title, "artist": song.Song.artist} for song in songs]
        })

    return {
        "success": True,
        "data": playlists_with_songs,
        "message": f"Retrieved {len(playlists_with_songs)} playlists",
        "meta": {"user_id": user_id, "count": len(playlists_with_songs)}
    }

@router.get("/{playlist_id}")
async def get_playlist(
    playlist_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Get a specific playlist with its songs."""
    user_id = current_user["uid"]
    
    # Validate playlist ownership
    playlist = await get_user_playlist(playlist_id, user_id, session)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found or access denied")
    
    # Fetch songs for the playlist
    song_query = select(PlaylistSong, Song).join(Song, PlaylistSong.song_id == Song.id).where(
        PlaylistSong.playlist_id == playlist_id
    )
    song_result = await session.execute(song_query)
    songs = song_result.all()
    
    return {
        "success": True,
        "data": {
            "id": playlist.id,
            "name": playlist.name,
            "description": playlist.description,
            "user_id": playlist.user_id,
            "song_count": len(songs),
            "songs": [{"id": song.Song.id, "title": song.Song.title, "artist": song.Song.artist} for song in songs]
        },
        "message": f"Retrieved playlist '{playlist.name}'"
    }

@router.delete("/{playlist_id}")
async def delete_playlist(
    playlist_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Delete a playlist."""
    user_id = current_user["uid"]
    
    # Validate playlist ownership
    playlist = await get_user_playlist(playlist_id, user_id, session)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found or access denied")

    # Delete all songs in the playlist first
    delete_songs_query = delete(PlaylistSong).where(PlaylistSong.playlist_id == playlist_id)
    await session.execute(delete_songs_query)

    # Delete the playlist
    delete_playlist_query = delete(Playlist).where(Playlist.id == playlist_id)
    await session.execute(delete_playlist_query)
    await session.commit()
    
    return {
        "success": True,
        "data": {"playlist_id": playlist_id, "name": playlist.name},
        "message": f"Playlist '{playlist.name}' deleted successfully"
    }

@router.delete("/{playlist_id}/songs/{song_id}")
async def delete_song_from_playlist(
    playlist_id: str,
    song_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Delete a song from a playlist."""
    user_id = current_user["uid"]
    
    # Validate playlist ownership
    playlist = await get_user_playlist(playlist_id, user_id, session)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found or access denied")
    
    # Find the playlist song
    query = select(PlaylistSong, Song).join(Song, PlaylistSong.song_id == Song.id).where(
        PlaylistSong.playlist_id == playlist_id, 
        PlaylistSong.song_id == song_id
    )
    result = await session.execute(query)
    playlist_song_data = result.first()
    if not playlist_song_data:
        raise HTTPException(status_code=404, detail="Song not found in playlist")

    # Delete the song from playlist
    delete_query = delete(PlaylistSong).where(
        PlaylistSong.playlist_id == playlist_id, 
        PlaylistSong.song_id == song_id
    )
    await session.execute(delete_query)
    await session.commit()
    
    return {
        "success": True,
        "data": {
            "playlist_id": playlist_id,
            "song_id": song_id,
            "song_title": playlist_song_data.Song.title
        },
        "message": f"Song '{playlist_song_data.Song.title}' removed from playlist '{playlist.name}'"
    }
