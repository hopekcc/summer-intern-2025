# HopeKCC API Routes

## Authentication

All API endpoints (unless otherwise noted) require a valid Firebase ID token for authentication. Clients must include this token as a **Bearer** token in the `Authorization` header for HTTP requests. For WebSocket connections, the token should be provided via the `X-Firebase-Token` header or as a `token` query parameter during connection. Unauthorized or expired tokens will result in a `401 Unauthorized` error.

## Basic Endpoints

### GET `/`
Returns a simple message indicating that the FastAPI server is online. This endpoint does not require authentication.

**Response:**
```json
{ "message": "FastAPI server is online. No authentication needed." }
```

### GET `/protected`
A test endpoint that requires authentication. It returns a message confirming access and echoes back the authenticated user's ID and email from the decoded token.

**Response (requires valid token):**
```json
{
  "message": "Access granted to protected route!",
  "user": {
    "uid": "<user-id>",
    "email": "<user-email>"
  }
}
```

### GET `/health/db`
Database connectivity health check. Accepts an optional query parameter **`timeout`** (float, default 1.5 seconds). Attempts a simple `SELECT 1` on the database with the given timeout.

**Response:**
- If DB reachable:
  ```json
  {
    "status": "ok",
    "duration_ms": <time>,
    "detail": null
  }
  ```
- If failure or timeout (HTTP 503):
  ```json
  {
    "status": "error",
    "duration_ms": <time>,
    "detail": "<error>"
  }
  ```

## Songs API

_All **/songs** endpoints require a valid Firebase ID token._

### GET `/songs/`
List Songs with optional search and pagination.

**Query params:** `search` (optional), `limit` (default 50), `offset` (default 0).

**Response:**
```json
[
  { "id": 1, "title": "Amazing Grace", "artist": "Newton", "page_count": 2 }
]
```

### GET `/songs/list`
Download full song list (from pre-generated file).

**Response:** JSON array of all songs, or 404 if file missing, or 500 if decoding fails.

### GET `/songs/{song_id}`
Get Song Details.

**Response:**
```json
{
  "id": 1,
  "title": "Amazing Grace",
  "artist": "Newton",
  "page_count": 2,
  "pdf_url": "/songs/1/pdf",
  "total_pages": 2,
  "image_url": "/songs/1/image"
}
```

### GET `/songs/{song_id}/pdf`
Download Song PDF.

**Response:** `application/pdf` stream with caching headers. 404 if missing.

### GET `/songs/{song_id}/image`
Get Song Cover Image.

**Response:** `image/webp` with caching headers. 404 if missing.

### GET `/songs/{song_id}/page/{page_number}`
Get Song Page Image.

**Response:** `image/webp`. 404 if out of range or missing.

### GET `/songs/search/substring`
Substring search.

**Params:** `q`, `limit`.

**Response:**
```json
[
  { "song_id": "1", "title": "Amazing Grace", "artist": "Newton", "page_count": 2, "score": 0.9 }
]
```

### GET `/songs/search/similarity`
Trigram similarity search.

**Params:** `q`, `limit`.

**Response:** list of results with similarity scores.

### GET `/songs/search/text`
Full-text search.

**Params:** `q`, `limit`.

**Response:** list of results with text search rank.

## Playlists API

### POST `/playlists/`
Create Playlist.

**Body:**
```json
{ "name": "Sunday Worship", "songs": [1, 2, 3] }
```

**Response:**
```json
{ "id": 42, "name": "Sunday Worship" }
```

### POST `/playlists/{playlist_id}/songs`
Add song to playlist.

**Response:** success message, or 404 if song not found.

### GET `/playlists/`
List Playlists.

**Response:**
```json
[
  { "id": 42, "name": "Sunday Worship", "songs": [ ... ] }
]
```

### DELETE `/playlists/{playlist_id}`
Delete Playlist.

**Response:** success message or 404.

### DELETE `/playlists/{playlist_id}/songs/{song_id}`
Remove song from playlist.

**Response:** success message or 404.

## Rooms API

### POST `/rooms/`
Create a Room.

**Response:**
```json
{ "room_id": "ABC123" }
```

### POST `/rooms/{room_id}/join`
Join a Room.

**Response:**
```json
{ "message": "User <uid> joined room <room_id>" }
```

### POST `/rooms/{room_id}/leave`
Leave a Room.

**Response (host leaving):**
```json
{ "message": "Host left, room closed" }
```

**Response (participant leaving):**
```json
{ "message": "User <uid> left room <room_id>" }
```

### GET `/rooms/{room_id}`
Get Room Details.

**Response:**
```json
{
  "room_id": "ABC123",
  "host_id": "UID123",
  "current_song": "SONGID",
  "current_page": 1,
  "participants": ["UID123", "UID456"]
}
```

### POST `/rooms/{room_id}/song`
Select Song for Room (host only).

**Body:**
```json
{ "song_id": "1" }
```

**Response:**
```json
{
  "message": "Song selected successfully",
  "song_id": "1",
  "title": "Amazing Grace",
  "artist": "Newton",
  "total_pages": 2,
  "current_page": 1,
  "image_etag": "etag123"
}
```

### POST `/rooms/{room_id}/page`
Change page (host only).

**Body:**
```json
{ "page": 2 }
```

**Response:**
```json
{ "message": "Page update broadcasted." }
```

### GET `/rooms/{room_id}/pdf`
Download current song PDF for the room.

### GET `/rooms/{room_id}/image`
Get current page image.
```

## WebSocket Events

### Client → Server
- `join_room` – Join room. `{ "type": "join_room", "room_id": "ABC123" }`
- `leave_room` – Leave room. `{ "type": "leave_room" }`

### Server → Client
- `connection_success` – `{ "type": "connection_success", "user_id": "UID123" }`
- `join_room_success` – `{ "type": "join_room_success", "room_id": "ABC123" }`
- `room_left` – `{ "type": "room_left", "room_id": "ABC123" }`
- `error` – `{ "type": "error", "message": "..." }`
- `participant_joined` – `{ "type": "participant_joined", "user_id": "UID123" }`
- `participant_left` – `{ "type": "participant_left", "user_id": "UID123" }`
- `room_closed` – `{ "type": "room_closed", "room_id": "ABC123" }`
- `song_updated` – includes song metadata
- `page_updated` – includes current_page, song_id, image_etag
- `batched_update` – groups multiple messages