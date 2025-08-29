from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete
from scripts.runtime.database import Playlist, PlaylistSong, Song, get_db_session
from scripts.runtime.auth_middleware import get_current_user  # Import your auth middleware

router = APIRouter()

@router.post("/")
async def create_playlist(
    name: str,
    current_user: dict = Depends(get_current_user),  # Get the authenticated user
    session: AsyncSession = Depends(get_db_session)
):
    """Create a new playlist."""
    user_id = current_user["uid"]  # Extract user_id from the authenticated user
    playlist = Playlist(name=name, user_id=user_id)  # Use the user_id here
    session.add(playlist)
    await session.commit()
    await session.refresh(playlist)
    return {"message": "Playlist created successfully", "playlist_id": playlist.id}

@router.post("/{playlist_id}/songs")
async def add_song_to_playlist(
    playlist_id: str, song_id: str, session: AsyncSession = Depends(get_db_session)
):
    """Add a song to a playlist."""
    query = select(Song).where(Song.id == song_id)
    result = await session.execute(query)
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    playlist_song = PlaylistSong(playlist_id=playlist_id, song_id=song_id)
    session.add(playlist_song)
    await session.commit()
    return {"message": f"Song {song_id} added to playlist {playlist_id}"}

@router.get("/")
async def get_playlists(session: AsyncSession = Depends(get_db_session)):
    """Get all playlists with their songs."""
    query = select(Playlist)
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
            "songs": [{"id": song.Song.id, "name": song.Song.title} for song in songs]
        })

    return playlists_with_songs

@router.delete("/{playlist_id}")
async def delete_playlist(playlist_id: str, session: AsyncSession = Depends(get_db_session)):
    """Delete a playlist."""
    query = select(Playlist).where(Playlist.id == playlist_id)
    result = await session.execute(query)
    playlist = result.scalar_one_or_none()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # Delete all songs in the playlist first
    delete_songs_query = delete(PlaylistSong).where(PlaylistSong.playlist_id == playlist_id)
    await session.execute(delete_songs_query)

    # Delete the playlist
    delete_playlist_query = delete(Playlist).where(Playlist.id == playlist_id)
    await session.execute(delete_playlist_query)
    await session.commit()
    return {"message": f"Playlist {playlist_id} deleted successfully"}

@router.delete("/{playlist_id}/songs/{song_id}")
async def delete_song_from_playlist(
    playlist_id: str, song_id: str, session: AsyncSession = Depends(get_db_session)
):
    """Delete a song from a playlist."""
    query = select(PlaylistSong).where(
        PlaylistSong.playlist_id == playlist_id, PlaylistSong.song_id == song_id
    )
    result = await session.execute(query)
    playlist_song = result.scalar_one_or_none()
    if not playlist_song:
        raise HTTPException(status_code=404, detail="Song not found in playlist")

    delete_query = delete(PlaylistSong).where(
        PlaylistSong.playlist_id == playlist_id, PlaylistSong.song_id == song_id
    )
    await session.execute(delete_query)
    await session.commit()
    return {"message": f"Song {song_id} removed from playlist {playlist_id}"}
