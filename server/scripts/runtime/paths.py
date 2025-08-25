"""
Centralized path handling for the application.
This module provides all path-related dependencies used throughout the application.
"""

import os
from fastapi import Depends

# Base directory for path calculations
# Go up 3 levels: runtime/ -> scripts/ -> server/
_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_database_dir() -> str:
    """Returns the absolute path to the song database directory."""
    return os.path.join(_base_dir, "song_data")

def get_songs_dir(database_dir: str = Depends(get_database_dir)) -> str:
    """Returns the absolute path to the songs directory inside the database."""
    return os.path.join(database_dir, "songs")

def get_metadata_path(database_dir: str = Depends(get_database_dir)) -> str:
    """Returns the absolute path to the songs_metadata.json file."""
    return os.path.join(database_dir, "songs_metadata.json")

def get_songs_pdf_dir(database_dir: str = Depends(get_database_dir)) -> str:
    """Returns the absolute path to the songs_pdf directory."""
    return os.path.join(database_dir, "songs_pdf")

def get_songs_img_dir(database_dir: str = Depends(get_database_dir)) -> str:
    """Returns the absolute path to the songs_img directory."""
    return os.path.join(database_dir, "songs_img")

def get_room_database_dir() -> str:
    """Returns the absolute path to the room database directory."""
    return os.path.join(_base_dir, "room_database")

def get_songs_list_gzip_path(database_dir: str = Depends(get_database_dir)) -> str:
    """Returns the absolute path to the gzipped songs list file."""
    return os.path.join(database_dir, "songs_list.json.gz")
