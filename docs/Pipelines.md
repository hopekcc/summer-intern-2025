# HopeKCC Backend Pipelines (Combined, Implementation-Accurate)

_Last updated: September 2, 2025_

This document consolidates the **Expanded** write-up and the implementation corrections into one source of truth. It covers ingestion, search indexing, realtime sync, CI/CD, configuration, and concrete response/asset shapes.

---

## 0) High-Level Overview

- **Goal:** Serve a multi-user, room-based music reader that synchronizes **ChordPro** songs (PDF/WebP) in real time, with fast search and robust caching.
- **Core subsystems:**  
  1) **Song Ingestion** (GitHub → PDFs/WebP → DB + list)  
  2) **Search Indexing** (substring, trigram, FTS)  
  3) **Realtime Sync** (WebSocket events)  
  4) **CI/CD** (setup, tests, deploy, ingestion)  

[Insert Diagram: System Architecture]


---

## 1) Song Ingestion Pipeline

Responsible for syncing raw `.cho` from GitHub, generating PDFs + WebP images, and upserting metadata into Postgres. It blends **`retrieve_songs.py`** (GitHub/files) and **`songs_db_pipeline_wrapper.py`** (orchestration).

### 1.1 GitHub Sync (ChordPro)
- Connects to `hopekcc/song-db-chordpro` (or configured repo).  
- Recursively enumerates directories via GitHub API; collects `.cho`. Handles pagination.
- **Concurrency:** GitHub fetches use a fixed internal semaphore of **10** in `retrieve_songs.py` (not a CLI knob).
- Stores files in `song_data/songs/` with unique numeric IDs tracked in `songs_metadata.json`.
- **Orphans:** files removed upstream are deleted locally; metadata pruned.
- **Reconciliation:** untracked local files get re-registered to avoid drift.

### 1.2 PDF Rendering
- If `CHORDPRO_PATH` points to a valid binary, generate production-quality PDFs; else use a safe **monospaced fallback** renderer.
- Output: `song_data/songs_pdf/{song_id}.pdf`. A legacy title-based reader is still tolerated for backwards compatibility.
- Failures warn and continue (fault tolerance).

### 1.3 Image Generation (WebP)
- Converts PDFs → **WebP** via **PyMuPDF → PIL**.  
- Path: `song_data/songs_img/{song_id}/page_{n}.webp` (first page is the “cover”).  
- **Lazy regeneration:** skip if present unless `--regen-assets` is passed.
- **Concurrency:** `--concurrency N` (default **4**) controls **PDF/WebP processing** workers (not GitHub fetches).
- Served through: `/songs/{id}/image` (cover), `/songs/{id}/page/{n}` (page), `/rooms/{id}/image` (current song cover per room).

### 1.4 Database Upsert
- Extracts tags from ChordPro: `{title, artist, key, tempo, genre, language}`.
- Upsert = select-then-insert/update per song.
- **Batched commit:** commit once after processing to reduce load.

### 1.5 Compressed Songs List
- Minimal index served by `/songs/list` with an **envelope** (not a bare array):

```json
{
  "count": 1234,
  "songs": [
    { "id": 42, "filename": "amazing_grace.cho", "title": "Amazing Grace" }
  ]
}
```

[Insert Diagram: Ingestion & Asset Flow]


### 1.6 CLI Reference (Ingestion/Assets)
| Flag | Scope | Notes |
|---|---|---|
| `--sync-only` | ingestion | GitHub sync only (no populate) |
| `--populate-only` | ingestion | Populate DB/assets from local files only |
| `--dry-run` | ingestion | Log actions without writing |
| `--force-download` | ingestion | Re-download even if unchanged |
| `--no-cleanup` | ingestion | Keep temp artifacts |
| `--songs-only <IDs>` | ingestion | Process only specified song IDs |
| `--check-missing` | assets | Report missing PDFs/WebPs |
| `--verify-assets` | assets | Validate PDFs/WebPs |
| `--regen-assets` | assets | Force regenerate PDFs/WebPs |
| `--concurrency N` | assets | Worker count for PDF/WebP processing |
| `--reset-songs` | DB | Clear songs before repopulating |

> Not present: `--no-sync`, `--only-reset`.

---

## 2) Search Indexing Pipeline

Provides performant substring, **trigram similarity**, and **full-text search** (FTS).

### 2.1 Substring Search (`ILIKE` + pg_trgm)
- Ensure `pg_trgm` extension is installed.  
- GIN indexes on `songs.title` and `songs.artist` accelerate `ILIKE '%text%'` via trigram filtering.

### 2.2 Trigram Similarity
- Use `%` operator + `similarity()` to find approximate matches; order by similarity desc.  
- Ideal for “fuzzy title/artist” queries.

### 2.3 Full-Text Search (FTS)
- Controlled by `FTS_MODE ∈ {none, expr, column}`; **default: `column`**.
- `column` mode adds `ts` (`tsvector`) column updated as:
  `to_tsvector('simple', title || ' ' || artist)`
- Indexed with GIN; queries use `plainto_tsquery('simple', :q)`; rank via `ts_rank`.

### 2.4 Indexing Mode & Locks
- `ENABLE_SEARCH_INDEXES` = **on** by default.  
- `CONCURRENT_INDEXES` = **on** → uses `CREATE INDEX CONCURRENTLY` (non-blocking).  
- Dev can force blocking with `--blocking-indexes` (faster locally).  
- `--setup-search` ensures extensions/indexes/columns exist.

### 2.5 HTTP Search Endpoints
- `/songs/search/substring?q=grace`  
- `/songs/search/similarity?q=amzing`  
- `/songs/search/text?q=amazing grace`

[Insert Diagram: Search Index Architecture]


---

## 3) Realtime Sync Pipeline (WebSocket)

A dedicated WebSocket server keeps rooms in sync; REST is used for asset fetches.

### 3.1 Server & Rooms
- Runs beside FastAPI on port **8766** (override with `WEBSOCKET_PORT`).
- Managed by a room factory that tracks sockets per room and broadcasts events.
- HTTP endpoints (join/leave/song/page) publish into the WebSocket layer.

### 3.2 Events (Canonical Shapes)
```json
{ "type": "participant_joined", "room_id": 12, "uid": "abc123" }
{ "type": "participant_left",   "room_id": 12, "uid": "abc123" }
{ "type": "room_closed",        "room_id": 12 }

{
  "type": "song_updated",
  "room_id": 12,
  "song_id": 42,
  "title": "Amazing Grace",
  "artist": "John Newton",
  "total_pages": 2,
  "current_page": 1,
  "image_etag": "W/\"12345-1724639012\""
}
{
  "type": "page_updated",
  "room_id": 12,
  "song_id": 42,
  "current_page": 2,
  "total_pages": 2,
  "image_etag": "W/\"12345-1724639012\""
}
```

### 3.3 Caching (ETag Behavior)
- ETags are **weak**: `W/"<size>-<mtime>"`.
- **304 (If-None-Match)** short-circuit implemented for **`/rooms/{id}/image`**.
- `/songs/{id}/image` and `/songs/{id}/page/{n}` return files with `ETag` + `Cache-Control`, but do **not** 304 yet.

**Example headers**
```
ETag: W/"12345-1724639012"
Cache-Control: public, max-age=86400
```

[Insert Diagram: Realtime Message Flow]


---

## 4) CI/CD Pipeline

Automates environment setup, ingestion, search setup, testing, and deployment.

### 4.1 Environment Setup
- `setup.sh` creates venv, installs `requirements.txt`.
- Creates directories: `logs/`, `song_data/songs`, `song_data/songs_pdf`, `song_data/songs_img`.
- DB initialized with SQLModel/SQLAlchemy models.
- `validate_environment` checks required files/env.

### 4.2 Automated Ingestion on Deploy
- Deployment runs `songs_db_pipeline_wrapper.py`:
  - GitHub sync (as needed)
  - Asset generation (PDF/WebP)
  - DB upsert
  - `--setup-search` to ensure search infra
  - `--fts-mode {none|expr|column}` (default `column`)

### 4.3 CI (Testing)
- Pytest with markers: `unit`, `integration`, `slow`.  
- `pytest-cov` for coverage; merges require passing tests.  
- Tests cover ingestion, search, WebSocket paths.

### 4.4 CD (Deployment)
- After CI, provision env, run ingestion/index setup, and restart Uvicorn (FastAPI + WebSocket).  
- `--blocking-indexes` may be used locally; production keeps concurrent creation.

[Insert Diagram: CI/CD & Deployment Flow]


---

## 5) Configuration Reference

### 5.1 Environment Variables
- `CHORDPRO_PATH` — Path to ChordPro binary (optional; enables high-quality PDFs).
- `WEBSOCKET_PORT` — Port for realtime server (default **8766**).
- `FIREBASE_JSON` — Firebase credentials (JSON string).
- `DB_STARTUP_CHECK` — Enable DB health check at startup.
- `DB_HEALTHCHECK_TIMEOUT` — Health check timeout.
- `FAIL_ON_DB_STARTUP_ERROR` — Abort if DB is unavailable.

### 5.2 File & Directory Layout
```
song_data/
  songs/                    # raw .cho inputs
  songs_pdf/                # {song_id}.pdf
  songs_img/
    {song_id}/page_{n}.webp
logs/
```
- Song list endpoint: `/songs/list` (JSON envelope with `count` + `songs[]`).

### 5.3 Service Ports
- WebSocket server: **8766** (override via env).  
- FastAPI/Uvicorn: per service config/systemd.

---

## 6) API Quick Reference (Selected)

- `GET /songs/list` → minimal index envelope (see §1.5)  
- `GET /songs/{id}/image` → cover image (WebP)  
- `GET /songs/{id}/page/{n}` → specific page (WebP)  
- `GET /rooms/{id}/image` → room’s current song cover (WebP, 304-aware)  
- `POST /rooms/{id}/join` → register participant + broadcast  
- `POST /rooms/{id}/leave` → deregister + broadcast  
- `POST /rooms/{id}/song` → host sets song + broadcast  
- `POST /rooms/{id}/page` → host sets page + broadcast  
- `GET /songs/search/substring?q=...`  
- `GET /songs/search/similarity?q=...`  
- `GET /songs/search/text?q=...`

---

## 7) Operational Notes

- Fault tolerance: ingestion logs and continues on per-file failures.  
- Idempotency: syncing + upserts are safe to re-run.  
- Performance: cache headers + ETags minimize bandwidth; DB writes batched.

---

## 8) Appendix: Response & Event Shapes

### 8.1 `/songs/list`
```json
{
  "count": 1234,
  "songs": [
    { "id": 42, "filename": "amazing_grace.cho", "title": "Amazing Grace" }
  ]
}
```

### 8.2 WebSocket Events
See §3.2 for the canonical examples.

### 8.3 HTTP Cache Headers
```
ETag: W/"<size>-<mtime>"
Cache-Control: public, max-age=86400
```

---

### Change Log
- **2025-09-02:** Consolidated expanded doc + corrections; clarified ETag/304 behavior; fixed concurrency & CLI flags; added endpoint list and quick ops notes.