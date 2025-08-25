from sqlmodel import SQLModel, Field, Session, select, create_engine, delete
from typing import List, Optional
from datetime import datetime, timezone
import os
import random
import string
import json
from fastapi import HTTPException

# Database setup - Updated path for scripts directory
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up to server directory
DATABASE_URL = f"sqlite:///{os.path.join(base_dir, 'room_database', 'rooms.db')}"
engine = create_engine(DATABASE_URL, echo=False)  # Set echo=True for SQL logging

class RoomParticipant(SQLModel, table=True):
    room_id: str = Field(foreign_key="room.room_id", primary_key=True)
    user_id: str = Field(primary_key=True)
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RoomAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(foreign_key="room.room_id")
    action_type: str
    user_id: Optional[str] = None
    data: Optional[str] = None  # JSON string for flexible data
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Room(SQLModel, table=True):
    room_id: str = Field(primary_key=True)
    host_id: str
    current_song: Optional[str] = None
    current_page: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

def init_database():
    """Create database tables"""
    # Extract the file path from the SQLite URL
    db_path = DATABASE_URL.replace("sqlite:///", "")
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    print(f"Initializing database at: {db_path}")
    SQLModel.metadata.create_all(engine)
    print("Database initialized successfully!")

# Database helper functions
def get_room(room_id: str) -> Optional[dict]:
    """Get a single room with participants"""
    with Session(engine) as session:
        room = session.exec(select(Room).where(Room.room_id == room_id)).first()
        if not room:
            return None
        
        # Get participants
        participants = session.exec(
            select(RoomParticipant.user_id).where(RoomParticipant.room_id == room_id)
        ).all()
        
        return {
            "room_id": room.room_id,
            "host_id": room.host_id,
            "current_song": room.current_song,
            "current_page": room.current_page,
            "participants": participants
        }

def get_all_rooms() -> List[dict]:
    """Get all rooms (for admin/debugging)"""
    with Session(engine) as session:
        rooms = session.exec(select(Room)).all()
        result = []
        for room in rooms:
            participants = session.exec(
                select(RoomParticipant.user_id).where(RoomParticipant.room_id == room.room_id)
            ).all()
            result.append({
                "room_id": room.room_id,
                "host_id": room.host_id,
                "current_song": room.current_song,
                "current_page": room.current_page,
                "participants": participants
            })
        return result

def update_room(room_id: str, update_func):
    """Atomically update a room"""
    with Session(engine) as session:
        room = session.exec(select(Room).where(Room.room_id == room_id)).first()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Convert to dict for update function
        room_dict = {
            "room_id": room.room_id,
            "host_id": room.host_id,
            "current_song": room.current_song,
            "current_page": room.current_page,
            "participants": [
                p.user_id for p in session.exec(
                    select(RoomParticipant).where(RoomParticipant.room_id == room_id)
                ).all()
            ]
        }
        
        # Apply update
        update_func(room_dict)
        
        # Update database
        room.host_id = room_dict["host_id"]
        room.current_song = room_dict["current_song"]
        room.current_page = room_dict["current_page"]
        room.updated_at = datetime.now(timezone.utc)
        
        # Update participants
        session.exec(delete(RoomParticipant).where(RoomParticipant.room_id == room_id))
        for user_id in room_dict["participants"]:
            participant = RoomParticipant(room_id=room_id, user_id=user_id)
            session.add(participant)
        
        session.commit()
        return room_dict

def create_room_db(room_id: str, host_id: str) -> dict:
    """Create a new room and delete host's old room"""
    with Session(engine) as session:
        # Delete host's existing room first
        old_room = session.exec(select(Room).where(Room.host_id == host_id)).first()
        if old_room:
            # Delete old room and all its data
            session.exec(delete(RoomParticipant).where(RoomParticipant.room_id == old_room.room_id))
            session.exec(delete(RoomAction).where(RoomAction.room_id == old_room.room_id))
            session.delete(old_room)
            print(f"Deleted host {host_id}'s old room: {old_room.room_id}")
        
        # Create new room
        room = Room(room_id=room_id, host_id=host_id)
        session.add(room)
        
        # Add host as participant
        participant = RoomParticipant(room_id=room_id, user_id=host_id)
        session.add(participant)
        
        # Log action
        action = RoomAction(
            room_id=room_id,
            action_type="room_created",
            user_id=host_id,
            data=json.dumps({"timestamp": datetime.now(timezone.utc).isoformat()})
        )
        session.add(action)
        
        session.commit()
        return {
            "room_id": room.room_id,
            "host_id": room.host_id,
            "current_song": room.current_song,
            "current_page": room.current_page,
            "participants": [host_id]
        }

def generate_room_id_db(length=6) -> str:
    """Generate unique room ID"""
    with Session(engine) as session:
        while True:
            room_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            existing = session.exec(select(Room).where(Room.room_id == room_id)).first()
            if not existing:
                return room_id

def log_room_action(room_id: str, action_type: str, user_id: Optional[str] = None, data: Optional[dict] = None):
    """Log a room action"""
    with Session(engine) as session:
        action = RoomAction(
            room_id=room_id,
            action_type=action_type,
            user_id=user_id,
            data=json.dumps(data) if data else None
        )
        session.add(action)
        session.commit()

def delete_room(room_id: str):
    """Delete a room and all its data"""
    with Session(engine) as session:
        # Delete participants first
        session.exec(delete(RoomParticipant).where(RoomParticipant.room_id == room_id))
        # Delete actions
        session.exec(delete(RoomAction).where(RoomAction.room_id == room_id))
        # Delete room
        room = session.exec(select(Room).where(Room.room_id == room_id)).first()
        if room:
            session.delete(room)
            session.commit()

# ============================================================================
# NON-DATABASE MODELS (for request/response validation)
# ============================================================================

from pydantic import BaseModel

class SongMetadata(BaseModel):
    """Pydantic model for song metadata responses."""
    id: str
    title: str
    artist: Optional[str] = None
    # Add any other metadata fields you have, e.g., genre, year
 