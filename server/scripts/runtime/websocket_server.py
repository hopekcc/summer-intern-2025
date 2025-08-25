import json
import asyncio
import os
import uuid
import time
from typing import Dict, List, Optional, Set, Any, Union

from autobahn.asyncio.websocket import WebSocketServerProtocol, WebSocketServerFactory

# Import centralized auth middleware
from scripts.runtime.auth_middleware import authenticate_websocket, verify_room_host

from scripts.runtime.logger import logger as _app_logger, set_request_id, reset_request_id
from scripts.runtime.database import get_db_session, get_room_by_id_from_db, get_song_by_id_from_db, Room, Song

# Child logger and WS config
logger = _app_logger.getChild("ws")
REQUEST_ID_HEADER = os.getenv("REQUEST_ID_HEADER", "X-Request-ID")

class MusicRoomProtocol(WebSocketServerProtocol):
    # WebSocket protocol for handling music room connections and events
    
    def onConnect(self, request):
        # Normalize headers for case-insensitive access
        try:
            headers_lower = {k.lower(): v for k, v in getattr(request, 'headers', {}).items()}
        except Exception:
            headers_lower = {}
        # Assign request ID (propagate if provided)
        rid_header_lower = REQUEST_ID_HEADER.lower()
        self.request_id = headers_lower.get(rid_header_lower, str(uuid.uuid4()))
        token = set_request_id(getattr(self, 'request_id', None))
        logger.info(
            "WS connect",
            extra={
                "request_id": self.request_id,
                "client_ip": getattr(request, 'peer', 'unknown'),
            },
        )
        reset_request_id(token)
        self.user_id = None
        self.room_id = None
        self.auth_token = None
        
        # Extract auth token from headers or query params (case-insensitive)
        if 'x-firebase-token' in headers_lower:
            self.auth_token = headers_lower['x-firebase-token']
        else:
            params = getattr(request, 'params', {})
            try:
                if 'token' in params:
                    t = params['token']
                    self.auth_token = t[0] if isinstance(t, (list, tuple)) else t
            except Exception:
                pass

    async def onOpen(self):
        # Handle WebSocket connection and authentication
        token = set_request_id(getattr(self, 'request_id', None))
        try:
            if not self.auth_token:
                logger.warning(
                    "WS rejected: missing auth token",
                    extra={"request_id": getattr(self, 'request_id', '-'), "client_ip": getattr(self, 'peer', 'unknown')},
                )
                self.sendClose(code=4000, reason="Authentication required")
                return

            # Use centralized authentication
            result = await authenticate_websocket(self.auth_token)

            # Check if authentication failed
            if 'error' in result:
                logger.warning(
                    "WS auth failed",
                    extra={"request_id": self.request_id, "client_ip": getattr(self, 'peer', 'unknown'), "status_code": result.get('status')},
                )
                # Use valid WebSocket close code (4000-4999 range for custom codes)
                close_code = 4001  # Custom: Authentication failed
                self.sendClose(code=close_code, reason=result['error'])
                return


            # Authentication succeeded
            self.user_id = result['uid']

            # Initialize per-connection send queue and writer
            self._init_send_queue()

            # Register this connection with the factory
            self.factory.register_connection(self)

            # Send confirmation message
            self.sendMessage(json.dumps({
                "type": "connection_success",
                "user_id": self.user_id
            }).encode('utf8'))
            logger.info(
                "WS connected",
                extra={"request_id": self.request_id, "uid": self.user_id, "client_ip": getattr(self, 'peer', 'unknown')},
            )
        finally:
            reset_request_id(token)
    
    def onMessage(self, payload, isBinary):
        # Handle incoming WebSocket messages
        token = set_request_id(getattr(self, 'request_id', None))
        try:
            if not isBinary:
                try:
                    message = json.loads(payload.decode('utf8'))
                    msg_type = message.get('type')
                    
                    if msg_type == 'join_room':
                        asyncio.create_task(self.handle_join_room(message))
                    elif msg_type == 'leave_room':
                        asyncio.create_task(self.handle_leave_room(message))
                    else:
                        logger.warning(
                            "WS unknown message type",
                            extra={"request_id": getattr(self, 'request_id', '-'), "uid": self.user_id, "room_id": getattr(self, 'room_id', None), "ws_event": "unknown_type", "msg_type": msg_type},
                        )
                except json.JSONDecodeError:
                    logger.warning(
                        "WS invalid JSON",
                        extra={"request_id": getattr(self, 'request_id', '-'), "uid": self.user_id, "room_id": getattr(self, 'room_id', None)},
                    )
                except Exception as e:
                    logger.error(
                        "WS message handling error",
                        exc_info=True,
                        extra={"request_id": getattr(self, 'request_id', '-'), "uid": self.user_id, "room_id": getattr(self, 'room_id', None)},
                    )
            else:
                # Binary messages are currently ignored
                pass
        finally:
            reset_request_id(token)
    
    async def handle_join_room(self, message):
        # Handle request to join a room
        token = set_request_id(getattr(self, 'request_id', None))
        room_id = message.get('room_id')
        if not room_id:
            self.send_error("No room_id provided")
            reset_request_id(token)
            return
        
        # Verify the room exists in the database
        try:
            async for session in get_db_session():
                room = await get_room_by_id_from_db(session, room_id)
                if not room:
                    # We'll allow joining non-existent rooms since they might be created later
                    # This improves reliability when rooms are created via REST API
                    pass
        except Exception as e:
            logger.error(f"Database error while verifying room {room_id}: {e}")
            # Continue despite errors for better resilience
        
        old_room = self.room_id
        self.room_id = room_id
        self.factory.join_room(self, room_id)
        
        # If previously in another room, leave it
        if old_room and old_room != room_id:
            self.factory.leave_room(self, old_room)
            logger.info(
                "WS moved rooms",
                extra={"request_id": getattr(self, 'request_id', '-'), "uid": self.user_id, "room_id": room_id},
            )
        else:
            logger.info(
                "WS joined room",
                extra={"request_id": getattr(self, 'request_id', '-'), "uid": self.user_id, "room_id": room_id},
            )
            
        # Send a success message
        self.sendMessage(json.dumps({"type": "join_room_success", "room_id": room_id}).encode('utf8'))
        reset_request_id(token)
        return
    
    async def handle_leave_room(self, message):
        # Handle request to leave current room
        token = set_request_id(getattr(self, 'request_id', None))
        if not self.room_id:
            self.send_error("Not in any room")
            reset_request_id(token)
            return
            
        room_id = self.room_id
        # Notify other room members BEFORE removing membership to ensure the room still exists
        asyncio.create_task(self.factory.broadcast_to_room(room_id, {
            "type": "participant_left",
            "user_id": self.user_id
        }, exclude=self))
        
        # Now remove from the room registry
        self.factory.leave_room(self, room_id)
        self.room_id = None
        
        # Send confirmation to the sender
        self.sendMessage(json.dumps({
            "type": "room_left",
            "room_id": room_id
        }).encode('utf8'))
        logger.info(
            "WS left room",
            extra={"request_id": getattr(self, 'request_id', '-'), "uid": self.user_id, "room_id": room_id},
        )
        reset_request_id(token)
    
    def onClose(self, wasClean, code, reason):
        # Handle WebSocket connection closing
        token = set_request_id(getattr(self, 'request_id', None))
        # Clean up room membership if needed
        room_id = getattr(self, 'room_id', None)
        if room_id:
            # Notify others BEFORE removing membership to avoid missing room warnings
            asyncio.create_task(self.factory.broadcast_to_room(room_id, {
                "type": "participant_left",
                "user_id": getattr(self, 'user_id', 'unknown')
            }, exclude=self))
            # Now remove and log
            self.factory.leave_room(self, room_id)
            logger.info(
                "WS disconnected in room",
                extra={"request_id": getattr(self, 'request_id', '-'), "uid": getattr(self, 'user_id', 'unknown'), "room_id": room_id},
            )
            logger.info(
                "WS removed from room after disconnect",
                extra={"request_id": getattr(self, 'request_id', '-'), "uid": getattr(self, 'user_id', 'unknown'), "room_id": room_id},
            )
        else:
            logger.info(
                "WS disconnected",
                extra={"request_id": getattr(self, 'request_id', '-'), "uid": getattr(self, 'user_id', 'unknown')},
            )

        # Unregister connection
        if hasattr(self, 'user_id') and self.user_id:
            self.factory.unregister_connection(self)
        # Stop writer and clear queue
        try:
            self._close_send_queue()
        except Exception:
            pass
        reset_request_id(token)
    
    def send_json(self, data):
        """Send a JSON message to the client."""
        self.sendMessage(json.dumps(data).encode('utf8'))
    
    def send_error(self, message):
        """Send an error message to the client."""
        self.send_json({
            "type": "error",
            "message": message
        })

    # --- Backpressure & queueing helpers ---
    def _init_send_queue(self):
        # Read settings from factory (with fallbacks)
        f = getattr(self, 'factory', None)
        self._ws_send_queue_max = getattr(f, 'ws_send_queue_max', 100)
        self._ws_coalesce_window_ms = getattr(f, 'ws_coalesce_window_ms', 50)
        self._ws_drop_policy = getattr(f, 'ws_drop_policy', 'oldest')
        self._ws_yield_threshold = getattr(f, 'ws_yield_threshold_bytes', 262144)
        self._ws_slow_client_drop_threshold = getattr(f, 'ws_slow_client_disconnect_after_drops', 0)
        self._coalesce_types: Set[str] = getattr(f, 'coalesce_types', {"page_updated", "song_updated"})

        self._send_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=self._ws_send_queue_max)
        self._writer_task: Optional[asyncio.Task] = asyncio.create_task(self._writer())
        self._coalesce_until: float = 0.0
        self._coalesce_latest: Dict[str, Dict[str, Any]] = {}
        self._coalesce_task: Optional[asyncio.Task] = None
        self._dropped_count: int = 0
        self._peak_queue: int = 0
        self._closed: bool = False
        logger.debug("WS send queue initialized", extra={"uid": getattr(self, 'user_id', None), "max": self._ws_send_queue_max})

    def _close_send_queue(self):
        self._closed = True
        if self._writer_task and not self._writer_task.done():
            self._writer_task.cancel()
        # drain queue best-effort
        while not self._send_queue.empty():
            try:
                self._send_queue.get_nowait()
            except Exception:
                break

    def enqueue_message(self, message: Dict[str, Any]) -> bool:
        """Enqueue a JSON message with coalescing and drop policy. Returns True if accepted."""
        try:
            msg_type = message.get('type')
            now = time.monotonic()

            # Coalesce noisy types within window
            if msg_type in self._coalesce_types and self._ws_coalesce_window_ms > 0:
                window_s = self._ws_coalesce_window_ms / 1000.0
                # Start window if expired
                if now >= self._coalesce_until:
                    self._coalesce_until = now + window_s
                    # schedule flush
                    if not self._coalesce_task or self._coalesce_task.done():
                        self._coalesce_task = asyncio.create_task(self._flush_coalesced_after(window_s))
                # store latest and return (do not enqueue yet)
                self._coalesce_latest[msg_type] = message
                return True

            # Non-coalescable -> encode and enqueue now
            encoded = json.dumps(message).encode('utf8')
            if self._send_queue.full():
                # Apply drop policy
                policy = (self._ws_drop_policy or 'oldest').lower()
                if policy == 'newest':
                    self._dropped_count += 1
                    self._maybe_disconnect_for_drops()
                    logger.warning("WS drop newest", extra={"uid": getattr(self, 'user_id', None), "q": self._send_queue.qsize()})
                    return False
                # default: drop oldest
                try:
                    _ = self._send_queue.get_nowait()
                    self._dropped_count += 1
                    self._maybe_disconnect_for_drops()
                    logger.warning("WS drop oldest", extra={"uid": getattr(self, 'user_id', None), "q": self._send_queue.qsize()})
                except asyncio.QueueEmpty:
                    pass
            try:
                self._send_queue.put_nowait(encoded)
                self._peak_queue = max(self._peak_queue, self._send_queue.qsize())
                return True
            except asyncio.QueueFull:
                self._dropped_count += 1
                self._maybe_disconnect_for_drops()
                logger.error("WS queue full after drop", extra={"uid": getattr(self, 'user_id', None)})
                return False
        except Exception:
            logger.error("WS enqueue error", exc_info=True)
            return False

    async def _flush_coalesced_after(self, delay_s: float):
        try:
            await asyncio.sleep(delay_s)
            pending = self._coalesce_latest
            self._coalesce_latest = {}
            for _type, msg in pending.items():
                encoded = json.dumps(msg).encode('utf8')
                if self._send_queue.full():
                    policy = (self._ws_drop_policy or 'oldest').lower()
                    if policy != 'newest':
                        try:
                            _ = self._send_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    else:
                        # newest policy: skip enqueuing coalesced if full
                        self._dropped_count += 1
                        self._maybe_disconnect_for_drops()
                        logger.warning("WS coalesced drop newest", extra={"uid": getattr(self, 'user_id', None)})
                        continue
                try:
                    self._send_queue.put_nowait(encoded)
                    self._peak_queue = max(self._peak_queue, self._send_queue.qsize())
                except asyncio.QueueFull:
                    self._dropped_count += 1
                    self._maybe_disconnect_for_drops()
                    logger.error("WS coalesced queue full", extra={"uid": getattr(self, 'user_id', None)})
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.error("WS coalesce flush error", exc_info=True)

    def _maybe_disconnect_for_drops(self):
        if self._ws_slow_client_drop_threshold and self._dropped_count >= self._ws_slow_client_drop_threshold:
            try:
                self.sendClose(code=4002, reason="Too many dropped messages")
            except Exception:
                pass

    async def _writer(self):
        try:
            while not self._closed:
                payload = await self._send_queue.get()
                await self._send_bytes(payload)
                if len(payload) >= self._ws_yield_threshold:
                    await asyncio.sleep(0)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.error("WS writer error", exc_info=True)

    async def _send_bytes(self, payload: bytes):
        # Default send; async wrapper to allow testing overrides
        self.sendMessage(payload)


class MusicRoomFactory(WebSocketServerFactory):
    """WebSocket factory for managing music room connections and rooms."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Maps user_id -> protocol
        self.connections: Dict[str, MusicRoomProtocol] = {}
        # Maps room_id -> set of user_ids
        self.rooms: Dict[str, Set[str]] = {}
        # Message queues for batching (room_id -> list of messages)
        self.message_queues: Dict[str, List[Dict[str, Any]]] = {}
        # Start the periodic batch sending task
        self._start_periodic_flush()

        # --- Backpressure settings from env ---
        def _to_int(name: str, default: int) -> int:
            try:
                return int(os.getenv(name, str(default)))
            except Exception:
                return default

        self.ws_send_queue_max = _to_int('WS_SEND_QUEUE_MAX', 100)
        self.ws_coalesce_window_ms = _to_int('WS_COALESCE_WINDOW_MS', 50)
        self.ws_drop_policy = os.getenv('WS_DROP_POLICY', 'oldest')
        self.ws_auto_fragment_size = _to_int('WS_AUTO_FRAGMENT_SIZE', 65536)
        self.ws_max_message_bytes = _to_int('WS_MAX_MESSAGE_BYTES', 1048576)
        self.ws_yield_threshold_bytes = _to_int('WS_YIELD_THRESHOLD_BYTES', 262144)
        self.ws_slow_client_disconnect_after_drops = _to_int('WS_SLOW_CLIENT_DISCONNECT_AFTER_DROPS', 0)
        self.coalesce_types: Set[str] = {"page_updated", "song_updated"}

        # Apply Autobahn protocol options
        try:
            self.setProtocolOptions(
                autoFragmentSize=self.ws_auto_fragment_size,
                maxMessagePayloadSize=self.ws_max_message_bytes,
            )
            logger.info(
                "WS protocol options",
                extra={
                    "autoFragmentSize": self.ws_auto_fragment_size,
                    "maxMessagePayloadSize": self.ws_max_message_bytes,
                },
            )
        except Exception:
            logger.warning("WS setProtocolOptions failed", exc_info=True)
    
    def register_connection(self, protocol: MusicRoomProtocol):
        """Register a new connection."""
        if protocol.user_id:
            self.connections[protocol.user_id] = protocol
            logger.info("WS registered connection", extra={"uid": protocol.user_id})
    
    def unregister_connection(self, protocol: MusicRoomProtocol):
        """Unregister a connection."""
        if protocol.user_id and protocol.user_id in self.connections:
            del self.connections[protocol.user_id]
            logger.info("WS unregistered connection", extra={"uid": protocol.user_id})
    
    def join_room(self, protocol: MusicRoomProtocol, room_id: str):
        """Add a user to a room."""
        if not room_id in self.rooms:
            self.rooms[room_id] = set()
        
        self.rooms[room_id].add(protocol.user_id)
        logger.info("WS user joined room", extra={"uid": protocol.user_id, "room_id": room_id})
        logger.info("WS room member count", extra={"room_id": room_id, "recipient_count": len(self.rooms[room_id])})
    
    def leave_room(self, protocol: MusicRoomProtocol, room_id: str):
        """Remove a user from a room."""
        if room_id in self.rooms and protocol.user_id in self.rooms[room_id]:
            self.rooms[room_id].remove(protocol.user_id)
            logger.info("WS user left room", extra={"uid": protocol.user_id, "room_id": room_id})
            
            # Clean up empty rooms
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                logger.info("WS room removed (empty)", extra={"room_id": room_id})

            # Note: Room membership is handled through the REST API
            # Any database updates would be done there to maintain consistency

    async def broadcast_to_room(self, room_id: str, message: Dict[str, Any], exclude=None):
        """Queue a message to be sent to all users in a room."""
        if room_id not in self.rooms:
            logger.warning("Attempted to broadcast to non-existent room", extra={"room_id": room_id, "ws_event": message.get('type')})
            return
        
        # Skip batching for non-batchable message types
        non_batchable_types = ['critical_update', 'song_updated', 'page_updated']
        
        if message.get('type') in non_batchable_types:
            # Send immediately without batching
            self._send_to_room_users(room_id, message, exclude)
            return
            
        # Initialize queue if needed
        if room_id not in self.message_queues:
            self.message_queues[room_id] = []
        
        # Queue the message
        self.message_queues[room_id].append(message)
        logger.debug("WS queued message", extra={"room_id": room_id, "ws_event": message.get('type'), "chunk_count": len(self.message_queues[room_id])})
    
    def _start_periodic_flush(self):
        """Start the periodic flush task."""
        loop = asyncio.get_event_loop()
        loop.call_later(0.2, self._periodic_flush_callback)
        logger.info("WS periodic flush started")
        
    def _periodic_flush_callback(self):
        """Callback for periodic flushing of message queues."""
        try:
            # Schedule the next callback first
            loop = asyncio.get_event_loop()
            loop.call_later(0.2, self._periodic_flush_callback)
            
            # Process all queued messages
            for room_id in list(self.message_queues.keys()):
                if self.message_queues.get(room_id, []):
                    self._flush_message_queue(room_id)
        except Exception as e:
            logger.error("WS periodic flush error", exc_info=True)
            # Ensure the loop continues even if there's an error
            loop = asyncio.get_event_loop()
            loop.call_later(1, self._periodic_flush_callback)
    
    def _flush_message_queue(self, room_id: str):
        """Send all queued messages for a room."""
        if room_id not in self.message_queues or not self.message_queues[room_id]:
            return
            
        messages = self.message_queues[room_id]
        self.message_queues[room_id] = []
        
        # Don't batch if there's only one message
        if len(messages) == 1:
            self._send_to_room_users(room_id, messages[0])
            return
        
        # Batch compatible messages together
        batched_message = {
            "type": "batched_update",
            "data": {
                "messages": messages
            }
        }
        
        logger.info("WS flush batch", extra={"room_id": room_id, "chunk_count": len(messages)})
        self._send_to_room_users(room_id, batched_message)
    
    def _send_to_room_users(self, room_id: str, message: Dict[str, Any], exclude=None):
        """Send a message to all users in a room (no batching)."""
        if room_id not in self.rooms:
            logger.warning("Attempted to send to non-existent room", extra={"room_id": room_id, "ws_event": message.get('type')})
            return
        
        count = 0
        for user_id in self.rooms[room_id]:
            if user_id in self.connections and (not exclude or user_id != exclude.user_id):
                try:
                    accepted = self.connections[user_id].enqueue_message(message)
                    if accepted:
                        count += 1
                except Exception:
                    logger.error("WS enqueue to user failed", exc_info=True, extra={"uid": user_id})
        
        logger.debug("WS sent message", extra={"room_id": room_id, "ws_event": message.get('type'), "recipient_count": count})
        return count
    
    def register_room(self, room_id: str):
        """Register a room in the WebSocket server to synchronize with REST API.
        This allows broadcasting to a room before any client has joined via WebSocket.
        """
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            logger.info("WS room registered via API", extra={"room_id": room_id})
            return True
        return False
            
    async def broadcast_song_updated(self, room_id: str, song_data: Dict[str, Any]):
        """Broadcast a song update event (metadata only). Clients fetch image over HTTP."""
        if room_id not in self.rooms:
            logger.warning("Cannot broadcast song update to non-existent room", extra={"room_id": room_id})
            return
        
        # Format metadata for the update event (include optional image_etag for HTTP fetch)
        metadata = {
            'song_id': song_data.get('song_id'),
            'title': song_data.get('title'),
            'artist': song_data.get('artist'),
            'current_page': song_data.get('current_page', 1),
            'total_pages': song_data.get('total_pages', 1),
        }
        if song_data.get('image_etag') is not None:
            metadata['image_etag'] = song_data.get('image_etag')
        
        await self.broadcast_to_room(room_id, {
            "type": "song_updated",
            "data": metadata
        })
    
    async def broadcast_page_updated(self, room_id: str, page_data: Dict[str, Any]):
        """Send a page update event (metadata only). Clients fetch image over HTTP."""
        logger.info("WS page_updated broadcast", extra={"room_id": room_id, "page": page_data.get('current_page')})
        
        if room_id not in self.rooms:
            logger.warning("Attempted to send page update to non-existent room", extra={"room_id": room_id, "page": page_data.get('current_page')})
            return
        
        # Send page metadata without image data
        metadata = page_data.copy()
        
        logger.info("WS broadcasting page_updated", extra={"room_id": room_id, "recipient_count": len(self.rooms.get(room_id, []))})
        await self.broadcast_to_room(room_id, {
            "type": "page_updated",
            "data": metadata
        })

# Global factory instance
factory = None
server = None

async def start_websocket_server(host: str = '0.0.0.0', port: int = 8766):
    """Start the WebSocket server."""
    global factory, server
    
    factory = MusicRoomFactory(f"ws://{host}:{port}")
    factory.protocol = MusicRoomProtocol
    
    loop = asyncio.get_event_loop()
    server = await loop.create_server(
        factory, host, port
    )
    logger.info("WS server started", extra={"ws_event": "server_start", "path": f"ws://{host}:{port}"})
    return server

def get_websocket_factory() -> MusicRoomFactory:
    """Get the global WebSocket factory instance."""
    return factory
