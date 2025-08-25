from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        # WebSocket is already accepted in the endpoint
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        print(f"Client connected to room {room_id}. Total connections: {len(self.active_connections[room_id])}")

    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            print(f"Client disconnected from room {room_id}. Remaining connections: {len(self.active_connections[room_id])}")
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
                print(f"Room {room_id} has no more connections, removed from active connections")

    async def broadcast(self, room_id: str, message: dict):
        if room_id in self.active_connections:
            print(f"Broadcasting to {len(self.active_connections[room_id])} connections in room {room_id}")
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_json(message)
                    print(f"Successfully sent message to connection in room {room_id}")
                except Exception as e:
                    print(f"Failed to send message to connection in room {room_id}: {e}")
        else:
            print(f"No active connections in room {room_id}") 