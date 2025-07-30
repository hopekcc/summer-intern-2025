from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import FileResponse
from rapidfuzz import process, fuzz
import subprocess
import json
import os
import shutil

from server.dependencies import (
    verify_firebase_token, 
    get_songs_dir, 
    get_metadata_path, 
    get_songs_pdf_dir
)
router = APIRouter()

# ============================================================================
# SONG MANAGEMENT HELPERS
# ============================================================================

def listOfSongs(metadata_path: str = Depends(get_metadata_path)):
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

def specficSong(song_id: str, metadata_path: str = Depends(get_metadata_path)):
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    if song_id in metadata:
        return metadata[song_id]
    else:
        raise HTTPException(status_code=404, detail="Song not found")


# PDF conversion helpers
def convert_chordpro_to_pdf(input_file: str, output_file: str):
    """Converts a ChordPro file to PDF, checking for the 'chordpro' command first."""
    
    # Prioritize CHORDPRO_PATH from .env, but fall back to checking system PATH
    chordpro_cmd = os.getenv("CHORDPRO_PATH")
    
    # If the .env path isn't valid, check the system PATH
    if not chordpro_cmd or not os.path.exists(chordpro_cmd):
        chordpro_cmd = shutil.which("chordpro")

    if not chordpro_cmd:
        raise HTTPException(
            status_code=500,
            detail="ChordPro command not found. Please install it or set CHORDPRO_PATH in your .env file."
        )
    
    print("Running conversion:", input_file, "→", output_file)
    try:
        subprocess.run(
            [chordpro_cmd, "--output", output_file, input_file],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print("ChordPro conversion failed:", e.stderr)
        raise HTTPException(status_code=500, detail="Failed to convert ChordPro file")

def songPDFHelper(
    song_id: str,
    songs_dir: str = Depends(get_songs_dir),
    songs_pdf_dir: str = Depends(get_songs_pdf_dir),
    metadata_path: str = Depends(get_metadata_path)
):
    song_filename = specficSong(song_id, metadata_path)
    pdf_filename = os.path.splitext(song_filename)[0] + ".pdf"
    pdf_path = os.path.join(songs_pdf_dir, pdf_filename)
    
    if os.path.exists(pdf_path):
        return pdf_path

    # If PDF doesn't exist, create it
    os.makedirs(songs_pdf_dir, exist_ok=True)
    chordpro_path = os.path.join(songs_dir, song_filename)
    
    if not os.path.exists(chordpro_path):
        raise HTTPException(status_code=404, detail="ChordPro file not found.")

    convert_chordpro_to_pdf(chordpro_path, pdf_path)
    return pdf_path

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/list")
def get_songs_list(
    songs_data: dict = Depends(listOfSongs),
    current_user=Depends(verify_firebase_token)
):
    return songs_data

@router.get("/{song_id}")
def get_specific_song(
    song_id: str, 
    songs_dir: str = Depends(get_songs_dir),
    metadata_path: str = Depends(get_metadata_path),
    current_user=Depends(verify_firebase_token)
):
    song_filename = specficSong(song_id, metadata_path)
    song_path = os.path.join(songs_dir, song_filename)
    if not os.path.exists(song_path):
        raise HTTPException(status_code=404, detail="Song file not found")
    
    with open(song_path, "r") as f:
        content = f.read()
    return {"song_id": song_id, "content": content}

@router.get("/{song_id}/pdf")
def get_song_pdf(
    song_id: str, 
    pdf_path: str = Depends(songPDFHelper),
    current_user=Depends(verify_firebase_token)
):
    return FileResponse(
        path=pdf_path,
        filename=os.path.basename(pdf_path),
        media_type="application/pdf"
    )

@router.get("/search/{query}")
def search_songs(
    query: str, 
    songs_data: dict = Depends(listOfSongs),
    current_user=Depends(verify_firebase_token)
):
    if not query:
        return []
    
    titles = list(songs_data.values())
    
    # Use RapidFuzz to find the best matches
    # process.extract returns a list of tuples: (title, score, song_id)
    matches = process.extract(query, titles, scorer=fuzz.WRatio, limit=10)
    
    # Map titles back to song IDs
    song_id_map = {v: k for k, v in songs_data.items()}
    
    # Format the results
    results = [
        {"song_id": song_id_map[match[0]], "title": match[0], "score": match[1]}
        for match in matches if match[1] > 70  # Filter out low-score matches
    ]
    
    return results 