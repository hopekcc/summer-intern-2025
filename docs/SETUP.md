# Setup Guide (OnSleekApiQT Local + CDN)

This guide shows exactly how to configure your .env, run the app locally, pre-gzip the songs catalog manifest, and set up a CDN (Cloudflare). Follow sections in order.

## 1) .env configuration

The server expects `FIREBASE_JSON` (service account JSON string), required `DATABASE_URL` (PostgreSQL), `WEBSOCKET_PORT`, and `DB_ECHO`. Optional envs control startup health checks, DB logging, and image ETag hashing bits: `DB_STARTUP_CHECK`, `DB_HEALTHCHECK_TIMEOUT`, `FAIL_ON_DB_STARTUP_ERROR`, `DB_LOG_LEVEL`, `ETAG_BITS`.

Create a `server/.env` file (next to `server/main.py`) with:

```
# Required: paste your minified Firebase service account JSON here as ONE line
# Tip (PowerShell) to minify: (Get-Content .\service-account.json -Raw | ConvertFrom-Json | ConvertTo-Json -Compress)
FIREBASE_JSON={"type":"service_account","project_id":"<your-project>","private_key_id":"<id>","private_key":"-----BEGIN PRIVATE KEY-----\n<base64>\n-----END PRIVATE KEY-----\n","client_email":"<svc>@<your-project>.iam.gserviceaccount.com","client_id":"<id>","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/<svc>@<your-project>.iam.gserviceaccount.com"}

# Required: PostgreSQL connection URL (async)
# DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST:5432/DBNAME

# WebSocket port (main app proxies to this internally)
WEBSOCKET_PORT=8766

# SQLAlchemy engine echo (0/1)
DB_ECHO=0

# Optional: Startup DB health checks (see /health/db)
# DB_STARTUP_CHECK=true
# DB_HEALTHCHECK_TIMEOUT=2.0
# FAIL_ON_DB_STARTUP_ERROR=false

# Optional: DB logger verbosity (propagated into asyncpg/SQLAlchemy via shared handlers)
# DB_LOG_LEVEL=WARNING

# Optional: Strong ETag hashing bits for images (64, 128, 256). Default 128.
# ETAG_BITS=128
```

Notes:
- Ensure `private_key` newlines are literal `\n` sequences (not real newlines).
- The app reads `FIREBASE_JSON` in `server/main.py` using `json.loads`.
- `DATABASE_URL` is required and must be `postgresql+asyncpg://...`.

## 2) Install and run locally

- Python 3.10+
- Windows PowerShell recommended for commands below.

```
# Install Python deps
pip install -r server/requirements.txt

# Start FastAPI
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

- REST base: http://localhost:8000
- WS server starts automatically on `WEBSOCKET_PORT` (default 8766). In production, put it behind a reverse proxy at `/ws`.

## 3) Pre-gzip the songs catalog manifest (for fast /songs/list)

Goal: build a compact manifest (e.g., `catalog.json`), then gzip (`catalog.json.gz`) and serve with proper headers. This accelerates a commonly-used endpoint by letting the frontend fetch a cached, CDN-served snapshot.

Suggested compact schema:
```
[
  {"id":"<songId>","title":"...","artist":"...","page_count":3},
  ...
]
```

### 3a) Generate the JSON manifest (reads from existing DB)

Create a local script `server\scripts\setup\generate_catalog.py` similar to this (not required to commit yet):

```python
# server/scripts/setup/generate_catalog.py
import asyncio, json, os
from server.scripts.runtime.database import AsyncSessionLocal, Song
from sqlalchemy import select

OUTPUT = os.path.join(os.getcwd(), "catalog.json")

async def main():
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(Song.id, Song.title, Song.artist, Song.page_count))).all()
        data = [
            {"id": r[0], "title": r[1], "artist": r[2], "page_count": r[3]} for r in rows
        ]
        with open(OUTPUT, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))  # compact
        print(f"Wrote {OUTPUT} with {len(data)} songs")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```
python -m server.scripts.setup.generate_catalog
# or
python server/scripts/setup/generate_catalog.py
```

### 3b) Gzip the manifest

PowerShell-friendly Python one-liner to gzip with deterministic ETag:
```
python - <<PY
import gzip, hashlib
p="catalog.json"; gz=p+".gz"
raw=open(p,'rb').read()
open(gz,'wb').write(gzip.compress(raw, compresslevel=9))
print("ETag:", hashlib.sha256(raw).hexdigest())
print("Wrote", gz)
PY
```
Save the printed ETag for your CDN or for testing.

### 3c) Serve locally with headers

Simple dev server that sends JSON + gzip headers (run from the folder containing the files):

```python
# serve_gz.py
from http.server import SimpleHTTPRequestHandler, HTTPServer
import os, hashlib

ETAG = hashlib.sha256(open('catalog.json','rb').read()).hexdigest()

class H(SimpleHTTPRequestHandler):
    def end_headers(self):
        if self.path.endswith('.json.gz'):
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Encoding','gzip')
            self.send_header('Cache-Control','public, max-age=604800')
            self.send_header('ETag', ETAG)
        super().end_headers()

HTTPServer(('0.0.0.0',8081), H).serve_forever()
```

Run it:
```
python serve_gz.py
```
Test:
```
curl -I http://localhost:8081/catalog.json.gz
```

## 4) CDN setup (Cloudflare)

You can start with Cloudflare Free:

1) Add your domain to Cloudflare, update nameservers at your registrar.
2) DNS: create an `A` record to your origin (API/static host). Orange-cloud (proxied) it.
3) Caching rules (Rules > Cache Rules):
   - If URL path matches `/catalog/*` or `*.json.gz` -> Cache eligibility: Eligible, Cache TTL: 7 days, Browser TTL: Respect existing headers.
   - Enable Brotli (Speed > Optimization).
4) Origin headers: serve `Cache-Control: public, max-age=604800` and an `ETag` as shown above for the manifest.
5) Verify through Cloudflare:
```
curl -I https://your.domain/catalog.json.gz
# Look for CF-Cache-Status: HIT after second request
```

Note: For local-only testing without a public domain, skip Cloudflare and use the local server from step 3c.

## 5) What to do NOW (local testing checklist)

- Create `server/.env` as in section 1 and ensure the Firebase JSON is one line with `\n` in `private_key`.
- `pip install -r server/requirements.txt`
- `uvicorn server.main:app --reload --host 0.0.0.0 --port 8000`
- Build and serve your catalog manifest:
  - `python -m server.scripts.setup.generate_catalog`
  - `python` the gzip one-liner (3b)
  - `python serve_gz.py` (serves at http://localhost:8081/catalog.json.gz)
- Use `Authorization: Bearer <Firebase ID token>` when calling API endpoints.
- Optional: point your frontend to `SONGS_MANIFEST_URL=http://localhost:8081/catalog.json.gz` for list bootstrap.

Additional testing advised for OnSleekApiQT current behavior:
- WebSocket: connect to `ws://localhost:8766` with Bearer token, join a room, and observe `song_updated`/`page_updated` events carry metadata only with `image_etag`.
- Image fetch with ETag: call `GET /rooms/{room_id}/image` after a page/song update, then repeat with `If-None-Match: "<etag>"` to verify `304 Not Modified`.
- Health check (optional): hit `GET /health/db` (enable startup checks via `DB_STARTUP_CHECK=true`).

You’re ready to iterate locally; when you have a public origin, apply CDN steps in section 4. 

## 6) Search database setup (pg_trgm + optional FTS)

- Ensure your DB is PostgreSQL and `DATABASE_URL` uses `postgresql+asyncpg://...`.
- Two ways to set up search infra:
  - Run SQL directly: see `server/scripts/setup/enable_pg_trgm.sql` (enables `pg_trgm`, creates trigram GIN indexes; includes commented `CONCURRENTLY` variants).
  - Or use the retrieval script flags (recommended):

```
python server/scripts/setup/retrieve_songs.py --ensure-search-infra --fts-mode expr
```

- Environment controls:
  - `CONCURRENT_RUN`: when true, creates indexes with `CONCURRENTLY` (non-blocking). Default recommended on server. Locally you can skip it or set false.
  - `FTS_MODE`: one of `none` (default), `expr`, or `column`.
    - `expr`: expression GIN index on `to_tsvector('simple', title || ' ' || artist)`.
    - `column`: adds a persistent `ts tsvector` column, populates it once, and creates a GIN index on it.

- Flags summary for `retrieve_songs.py`:
  - `--ensure-search-infra`: ensures `pg_trgm` + trigram indexes; honors `CONCURRENT_RUN` and `FTS_MODE`.
  - `--allow-blocking`: forces blocking index creation for this run (equivalent to `CONCURRENT_RUN=false`).
  - `--fts-mode {none,expr,column}`: override `FTS_MODE` for this run.

Once created, the following endpoints become efficient:
- `GET /songs/search/substring?q=...`
- `GET /songs/search/similarity?q=...` (requires `pg_trgm`)
- `GET /songs/search/text?q=...` (benefits from FTS infra)
