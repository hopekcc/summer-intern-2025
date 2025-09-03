import os
import json
import asyncio
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables ASAP so DATABASE_URL is available before database engine creation
# Load the .env file located next to this file and override any pre-set env vars
_dotenv_path = Path(__file__).with_name('.env')
load_dotenv(_dotenv_path, override=True)
FIREBASE_JSON = os.getenv("FIREBASE_JSON")

import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.auth import InvalidIdTokenError
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from scripts.runtime.logger import logger
from scripts.runtime.database import create_db_and_tables_async as init_database
from scripts.runtime.database import engine as db_engine
from scripts.runtime.database import check_db_connectivity
from scripts.runtime.websocket_server import start_websocket_server, get_websocket_factory
from scripts.runtime.paths import get_database_dir
from scripts.runtime.auth_middleware import get_current_user
from routers import songs, rooms, playlists

# Initialize FastAPI app
app = FastAPI()

# ===================================================================
# App State and Lifespan Events
# ===================================================================
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up the application...")
    await init_database()
    logger.info("Database initialized.")
    # Log which database/dialect we actually connected to
    try:
        db_url = db_engine.url.render_as_string(hide_password=True)
        logger.info(f"DB Dialect: {db_engine.dialect.name} | URL: {db_url}")
    except Exception:
        logger.warning("Could not introspect database engine URL", exc_info=True)
    
    # Optional startup DB connectivity healthcheck
    try:
        do_check = os.getenv("DB_STARTUP_CHECK", "false").lower() in ("1", "true", "yes")
        timeout = float(os.getenv("DB_HEALTHCHECK_TIMEOUT", "2.0"))
        fail_on_error = os.getenv("FAIL_ON_DB_STARTUP_ERROR", "false").lower() in ("1", "true", "yes")
        if do_check:
            ok, detail, dur_ms = await check_db_connectivity(timeout_seconds=timeout)
            if ok:
                logger.info(f"DB startup healthcheck ok in {dur_ms:.1f}ms")
            else:
                logger.error("DB startup healthcheck failed", extra={"error": detail, "duration_ms": round(dur_ms, 1)})
                if fail_on_error:
                    raise RuntimeError(f"DB healthcheck failed: {detail}")
    except Exception as e:
        # If fail_on_error is true, this will bubble; otherwise, log and continue
        if os.getenv("FAIL_ON_DB_STARTUP_ERROR", "false").lower() in ("1", "true", "yes"):
            raise
        logger.warning(f"Startup DB healthcheck encountered an error: {e}", exc_info=True)
    
    # Set up application state for WebSocket dependencies
    # We construct these paths at startup; dependencies will be used for requests
    database_dir = get_database_dir()
    app.state.songs_dir = os.path.join(database_dir, "songs")
    app.state.songs_pdf_dir = os.path.join(database_dir, "songs_pdf")
    app.state.metadata_path = os.path.join(database_dir, "songs_metadata.json")
    
    # Start WebSocket server in a separate thread
    ws_port = int(os.getenv("WEBSOCKET_PORT", 8766))
    loop = asyncio.get_event_loop()
    logger.info(f"Starting WebSocket server on port {ws_port}...")
    try:
        asyncio.ensure_future(start_websocket_server(port=ws_port))
        logger.info("WebSocket server started successfully.")
    except Exception as e:
        logger.error(f"Failed to start WebSocket server: {e}", exc_info=True)

# ===================================================================
# Middleware
# ===================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# ===================================================================
# API Routers
# ===================================================================
app.include_router(songs.router, prefix="/songs", tags=["songs"])
app.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
app.include_router(playlists.router, prefix="/playlists", tags=["playlists"])

# Initialize Firebase and database
if FIREBASE_JSON:
    service_account_info = json.loads(FIREBASE_JSON)
    cred = credentials.Certificate(service_account_info)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
else:
    raise ValueError("FIREBASE_JSON environment variable must be set")

 

# ============================================================================
# BASIC ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    return {"message": "FastAPI server is online. No authentication needed."}

@app.get("/protected")
def protected_route(user_data=Depends(get_current_user)):
    return {
        "message": "Access granted to protected route!",
        "user": {
            "uid": user_data.get("uid"),
            "email": user_data.get("email")
        }
    }

# ===================================================================
# Health Endpoints
# ===================================================================
@app.get("/health/db")
async def health_db(timeout: float = 1.5):
    ok, detail, dur_ms = await check_db_connectivity(timeout_seconds=timeout)
    status_code = 200 if ok else 503
    payload = {
        "status": "ok" if ok else "error",
        "duration_ms": round(dur_ms, 1),
        "detail": None if ok else detail,
    }
    return JSONResponse(payload, status_code=status_code)

