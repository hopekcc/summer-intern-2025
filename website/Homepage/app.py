
# app.py
# -----------------------------------------------------------------------------
# Flask app for the HOPEKCC Chord Pro Tool
# - Routes (home, preview, view PDF, search by artist/title, rooms, etc.)
# - Firebase Admin session handling (exchange ID token -> session cookie)
# - Helpers to get current user and protect routes
# - Logout returns to homepage; dashboard page not required
# - NEW: Rooms with random codes (create + join)
# - NEW: /pdf/stream/<song_id> proxy endpoint (no "page" param; server-side token verify)
# -----------------------------------------------------------------------------

import os
import re  # regex
import datetime
import random
import string
import requests  # NEW: for proxying to FastAPI
import logging  # Added logging

from flask import (
    Flask, render_template, request, send_from_directory,
    url_for, abort, make_response, redirect, jsonify, Response  # NEW: Response for streaming
)
from werkzeug.utils import secure_filename

import firebase_admin
from firebase_admin import credentials, auth as admin_auth

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Firebase Admin initialization
# -----------------------------------------------------------------------------
# Make sure serviceAccountKey.json is present in project root (DO NOT commit it)
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def verify_session_cookie(session_cookie: str):
    """Verify a Firebase session cookie."""
    try:
        return admin_auth.verify_session_cookie(session_cookie, check_revoked=True)
    except Exception as e:
        logger.error(f"Session cookie verification failed: {e}")
        return None

def current_user():
    """Return decoded user claims if a valid session cookie exists; otherwise None."""
    cookie = request.cookies.get("session")
    if not cookie:
        return None
    try:
        return verify_session_cookie(cookie)
    except Exception as e:
        logger.error(f"Current user verification failed: {e}")
        return None

@app.context_processor
def inject_user():
    """Make `user` available in ALL templates (e.g., navbar)."""
    return {"user": current_user()}

# NEW: Verify an ID token (used by the PDF proxy)
def verify_id_token(id_token: str):
    """Verify a Firebase ID token; return claims or None on failure."""
    try:
        return admin_auth.verify_id_token(id_token)
    except Exception as e:
        logger.error(f"ID token verification failed: {e}")
        return None

# Random Room Number Generator
def make_room_code(n: int = 6) -> str:
    """Generate a random room number, for example DMF50P。"""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))

# -----------------------------------------------------------------------------
# Session routes
# -----------------------------------------------------------------------------
@app.route("/sessionLogin", methods=["POST"])
def session_login():
    """Exchange Firebase ID token for secure session cookie."""
    data = request.get_json(silent=True) or {}
    id_token = data.get("idToken")
    if not id_token:
        return ("Missing idToken", 400)

    expires_in = datetime.timedelta(days=5)
    try:
        session_cookie = admin_auth.create_session_cookie(id_token, expires_in=expires_in)
    except Exception as e:
        return (f"Failed to create session cookie: {e}", 401)

    resp = make_response("ok")
    resp.set_cookie(
        "session",
        session_cookie,
        max_age=int(expires_in.total_seconds()),
        httponly=True,
        secure=False,  # ⚠️ Set to True when deploying to HTTPS
        samesite="Lax"
    )
    return resp

@app.route("/logout")
def logout():
    """Clear the session cookie and redirect to home page."""
    resp = make_response(redirect(url_for("home")))
    resp.delete_cookie("session")
    return resp

# -----------------------------------------------------------------------------
# PDF/Preview config
# -----------------------------------------------------------------------------
PDF_FOLDER = os.path.join(app.root_path, "static", "pdfs")
app.config["PDF_FOLDER"] = PDF_FOLDER

# Where your FastAPI lives (edit env var in deployment)
BACKEND_BASE = os.environ.get("BACKEND_BASE", "http://34.125.143.141:8000")

# -----------------------------------------------------------------------------
# Utility
# -----------------------------------------------------------------------------
def make_slug(title: str) -> str:
    """Convert a title to safe PDF filename."""
    return re.sub(r"[^a-z0-9]", "", title.lower()) + ".pdf"

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("home.html", username="Mentor", insert_text="Welcome to our demo!!!")

# PREVIEW
@app.route("/preview", methods=["GET", "POST"])
def preview():
    if request.method == "POST":
        chordpro_text = request.form.get("chordpro_text")
        return render_template("preview.html", content=chordpro_text)
    return render_template("preview.html", content=None)

# PDF VIEWER (local sample PDFs under /static/pdfs)
@app.route("/view/<path:filename>")
def view_pdf(filename):
    filename = secure_filename(filename)
    file_path = os.path.join(app.config["PDF_FOLDER"], filename)
    if not os.path.exists(file_path):
        abort(404)
    return render_template("view.html", filename=filename)

@app.route("/pdfs/<path:filename>")
def serve_pdf(filename):
    return send_from_directory(app.config["PDF_FOLDER"], filename)

# -----------------------------------------------------------------------------
# NEW: Secure PDF proxy (no "page" param since FastAPI doesn't support it)
# -----------------------------------------------------------------------------
@app.route("/pdf/stream/<song_id>")
def pdf_stream(song_id):
    """
    Secure PDF proxy:
    - expects ?token=<Firebase_ID_token> in query
    - verifies token server-side
    - forwards to FastAPI with Authorization: Bearer <token>
    - streams PDF back to browser as application/pdf
    """
    id_token = request.args.get("token")
    if not id_token:
        abort(400, description="Missing token")

    claims = verify_id_token(id_token)
    if not claims:
        abort(401)

    url = f"{BACKEND_BASE}/songs/{song_id}/image"
    headers = {"Authorization": f"Bearer {id_token}"}

    try:
        upstream = requests.get(url, headers=headers, stream=True, timeout=30)
    except requests.RequestException:
        abort(502)

    if upstream.status_code != 200:
        abort(upstream.status_code)

    return Response(upstream.iter_content(8192), content_type="application/pdf")

# -----------------------------------------------------------------------------
# ARTIST SEARCH
# -----------------------------------------------------------------------------
@app.route("/search_artist")
def search_artist():
    artists = ["Andy", "Brandon", "Caleb", "Drake",
               "Edward", "Fred", "Grayson", "Humza",
               "Ismael", "John", "Kush", "Lawson",
               "Michelle", "Nick", "Owen", "Peter",
               "John", "Ryan", "Sophie", "Trevor",
               "Uno", "Vivian", "William", "Xanthos",
               "Yerson", "Zachery"]

    letter = request.args.get("letter", "A").upper()
    filtered = [artist for artist in artists if artist.upper().startswith(letter)]
    return render_template("search_artist.html", letter=letter, artists=filtered)

# -----------------------------------------------------------------------------
# TITLE SEARCH
# -----------------------------------------------------------------------------
@app.route("/search_title", methods=["GET", "POST"])
def search_title():
    all_songs = [
        "Finger Family Song", "Jingle Bells", "London Bridge is Falling Down",
        "Old McDonald Had A Farm", "Thomas and Friends Theme Song",
        "Fix You", "Believer", "Blinding Lights", "Starboy",
        "Love Story", "Love Me Like You Do", "Neveda"
    ]

    results, keyword = [], ""
    if request.method == "POST":
        keyword = (request.form.get("keyword", "")).strip().lower()
        for song in all_songs:
            if keyword in song.lower():
                filename = make_slug(song)
                pdf_url = url_for("view_pdf", filename=filename)
                results.append({"title": song, "pdf_url": pdf_url})
    return render_template("search_title.html", keyword=keyword, results=results)

# -----------------------------------------------------------------------------
# NEW: Rooms (random room code)
# -----------------------------------------------------------------------------
@app.route("/api/rooms", methods=["POST"])
def api_create_room():
    """AJAX: create random room code and create room in backend, then return JSON."""
    code = make_room_code()
    
    try:
        id_token = _extract_bearer_from_auth_header()
        if not id_token:
            # Try to get from JSON body as fallback
            data = request.get_json(silent=True) or {}
            id_token = data.get("idToken")
        
        if id_token:
            # Verify the token first
            claims = verify_id_token(id_token)
            if claims:
                # First try: POST /rooms/{room_id} (RESTful approach)
                url = f"{BACKEND_BASE}/rooms/{code}"
                headers = {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}
                
                logger.info(f"[DEBUG] Attempting room creation with POST /rooms/{code}")
                backend_response = requests.post(url, headers=headers, json={}, timeout=10)
                
                if backend_response.status_code not in [200, 201]:
                    # Second try: POST /rooms/ with room_id in body
                    logger.info(f"[DEBUG] First attempt failed, trying POST /rooms/ with body")
                    url = f"{BACKEND_BASE}/rooms/"
                    room_data = {"room_id": code}
                    backend_response = requests.post(url, headers=headers, json=room_data, timeout=10)
                
                logger.info(f"[DEBUG] Backend response: {backend_response.status_code} - {backend_response.text}")
                
                if backend_response.status_code in [200, 201]:
                    logger.info(f"Successfully created room {code} in backend")
                    return jsonify({"code": code, "created": True})
                else:
                    logger.warning(f"Backend room creation returned {backend_response.status_code}: {backend_response.text}")
                    try:
                        error_detail = backend_response.json()
                        logger.warning(f"Backend error details: {error_detail}")
                    except:
                        pass
                    # Still return the code even if backend creation failed
                    return jsonify({"code": code, "created": False, "error": backend_response.text})
            else:
                logger.warning("Invalid ID token provided for room creation")
                return jsonify({"code": code, "created": False, "error": "Invalid token"})
        else:
            logger.warning("No ID token provided for room creation")
            return jsonify({"code": code, "created": False, "error": "No token provided"})
            
    except requests.RequestException as e:
        logger.error(f"Failed to create room {code} in backend: {e}")
        return jsonify({"code": code, "created": False, "error": str(e)})
    except Exception as e:
        logger.error(f"Unexpected error creating room {code}: {e}")
        return jsonify({"code": code, "created": False, "error": str(e)})

@app.route("/rooms/create")
def create_room():
    """Generate a random room number and jump to the corresponding room."""
    code = make_room_code()
    
    user = current_user()
    if user:
        try:
            # Get a fresh ID token - this is tricky without frontend, so we'll create room on first access
            logger.info(f"Room {code} will be created on first access")
        except Exception as e:
            logger.error(f"Error preparing room {code}: {e}")
    
    return redirect(url_for("room_page", room_id=code))

@app.route("/rooms/join", methods=["GET", "POST"])
def join_room():
    if request.method == "POST":
        code = (request.form.get("room_code", "")).strip().upper()
        if not code:
            return render_template("join_room.html", error="Please enter the room code")
        return redirect(url_for("room_page", room_id=code))
    return render_template("join_room.html")

@app.route("/rooms/<room_id>")
def room_page(room_id):
    """Room page - create room in backend if it doesn't exist."""
    user = current_user()
    if user:
        try:
            # We can't easily get a fresh ID token here, so the room will be created
            # when the frontend makes its first API call with a valid token
            logger.info(f"Room {room_id} page accessed, will be created on first API call")
        except Exception as e:
            logger.error(f"Error preparing room {room_id}: {e}")
    
    return render_template("room.html", room_id=room_id)

# -----------------------------------------------------------------------------
# Songs page
# -----------------------------------------------------------------------------
@app.route("/songs")
def song_list():
    return render_template("songs.html")

# -----------------------------------------------------------------------------
# Dashboard (optional, redirect only)
# -----------------------------------------------------------------------------
@app.route("/dashboard")
def dashboard():
    if not current_user():
        return redirect(url_for("login_page"))
    return redirect(url_for("home"))

# -----------------------------------------------------------------------------
# Login page
# -----------------------------------------------------------------------------
@app.route("/login")
def login_page():
    force = request.args.get("force") == "1"
    if not force and current_user():
        return redirect(url_for("home"))
    return render_template("login.html")

# -----------------------------------------------------------------------------
# NEW: Get available songs from FastAPI
# -----------------------------------------------------------------------------
@app.route("/api/songs")
def api_get_songs():
    """Get list of available songs from FastAPI backend."""
    try:
        url = f"{BACKEND_BASE}/songs/"
        logger.info(f"Fetching songs from {url}")
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            songs_data = response.json()
            logger.info(f"Successfully fetched {len(songs_data)} songs")
            return jsonify(songs_data)
        else:
            logger.error(f"Failed to fetch songs: {response.status_code} - {response.text}")
            return jsonify({"error": "Failed to fetch songs"}), response.status_code
            
    except requests.RequestException as e:
        logger.error(f"Request to fetch songs failed: {e}")
        return jsonify({"error": "Backend service unavailable"}), 502

# -----------------------------------------------------------------------------
# Room API proxies
# -----------------------------------------------------------------------------
def _extract_bearer_from_auth_header():
    """Get 'Bearer xxx' from incoming request headers."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.split(" ", 1)[1].strip()
    return None

@app.route("/rooms/<room_id>/song", methods=["POST"])
def proxy_room_select_song(room_id):
    """
    Proxy: POST /rooms/{room_id}/song
    Body:  {"song_id": "<id>"}
    Auth:  front-end sends Authorization: Bearer <idToken>
    """
    id_token = _extract_bearer_from_auth_header()
    if not id_token:
        logger.warning(f"Missing Authorization header for room {room_id}")
        return jsonify({"error": "Missing Authorization header"}), 401

    claims = verify_id_token(id_token)
    if not claims:
        logger.warning(f"Invalid token for room {room_id}")
        return jsonify({"error": "Invalid authentication token"}), 401

    data = request.get_json(silent=True) or {}
    song_id = data.get("song_id", "").strip()
    if not song_id:
        logger.warning(f"Empty song_id for room {room_id}")
        return jsonify({"error": "Song ID is required"}), 400

    try:
        logger.info(f"[DEBUG] Ensuring room {room_id} exists before song selection")
        
        # First try: POST /rooms/{room_id}
        create_url = f"{BACKEND_BASE}/rooms/{room_id}"
        create_headers = {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}
        
        logger.info(f"[DEBUG] Attempting room creation with POST /rooms/{room_id}")
        create_response = requests.post(create_url, headers=create_headers, json={}, timeout=10)
        
        if create_response.status_code not in [200, 201, 409]:
            # Second try: POST /rooms/ with room_id in body
            logger.info(f"[DEBUG] First attempt failed, trying POST /rooms/ with body")
            create_url = f"{BACKEND_BASE}/rooms/"
            create_data = {"room_id": room_id}
            create_response = requests.post(create_url, headers=create_headers, json=create_data, timeout=10)
        
        logger.info(f"[DEBUG] Room creation response: {create_response.status_code} - {create_response.text}")
        
        if create_response.status_code in [200, 201]:
            logger.info(f"Room {room_id} created successfully")
        elif create_response.status_code == 409:
            logger.info(f"Room {room_id} already exists")
        else:
            logger.warning(f"Room creation returned {create_response.status_code}: {create_response.text}")
            
    except requests.RequestException as e:
        logger.error(f"Failed to ensure room {room_id} exists: {e}")
        # Continue anyway, maybe the room already exists

    url = f"{BACKEND_BASE}/rooms/{room_id}/song"
    logger.info(f"[DEBUG] Proxying song selection to {url} with song_id: {song_id}")
    
    try:
        upstream = requests.post(
            url,
            headers={"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"},
            json={"song_id": song_id},
            timeout=20,
        )
        
        logger.info(f"[DEBUG] Song selection response: {upstream.status_code} - {upstream.text}")
        
        if upstream.status_code != 200:
            error_text = upstream.text
            logger.error(f"Backend returned {upstream.status_code}: {error_text}")
            
            try:
                error_json = upstream.json()
                error_detail = error_json.get("detail", error_text)
                return jsonify({"error": f"Failed to select song ({upstream.status_code}): {error_detail}"}), upstream.status_code
            except:
                return jsonify({"error": f"Failed to select song ({upstream.status_code}): {error_text}"}), upstream.status_code
            
        logger.info(f"Successfully selected song {song_id} for room {room_id}")
        return jsonify({"success": True, "song_id": song_id})
        
    except requests.RequestException as e:
        logger.error(f"Request to backend failed: {e}")
        return jsonify({"error": "Backend service unavailable"}), 502

@app.route("/rooms/<room_id>/page", methods=["POST"])
def proxy_room_set_page(room_id):
    """
    Proxy: POST /rooms/{room_id}/page
    Body:  {"page": <int>}
    """
    id_token = _extract_bearer_from_auth_header()
    if not id_token:
        logger.warning(f"Missing Authorization header for room {room_id}")
        return jsonify({"error": "Missing Authorization header"}), 401

    claims = verify_id_token(id_token)
    if not claims:
        logger.warning(f"Invalid token for room {room_id}")
        return jsonify({"error": "Invalid authentication token"}), 401

    data = request.get_json(silent=True) or {}
    page = data.get("page")
    if page is None or not isinstance(page, int) or page < 1:
        logger.warning(f"Invalid page number for room {room_id}: {page}")
        return jsonify({"error": "Valid page number is required"}), 400

    url = f"{BACKEND_BASE}/rooms/{room_id}/page"
    logger.info(f"Proxying page setting to {url} with page: {page}")
    
    try:
        upstream = requests.post(
            url,
            headers={"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"},
            json={"page": page},
            timeout=20,
        )
        
        if upstream.status_code != 200:
            error_text = upstream.text
            logger.error(f"Backend returned {upstream.status_code}: {error_text}")
            return jsonify({"error": f"Backend error: {error_text}"}), upstream.status_code
            
        logger.info(f"Successfully set page {page} for room {room_id}")
        return jsonify({"success": True, "page": page})
        
    except requests.RequestException as e:
        logger.error(f"Request to backend failed: {e}")
        return jsonify({"error": "Backend service unavailable"}), 502

@app.route("/rooms/<room_id>/image", methods=["GET"])
def proxy_room_current_image(room_id):
    """
    Proxy: GET /rooms/{room_id}/image
    Query: ?token=<idToken>[&page=<int>]  (page : optional)
    - Verify token server-side (optional but recommended)
    - Forward to FastAPI with Authorization header
    - Stream image back (image/png or image/jpeg)
    """
   
    id_token = request.args.get("token")
    if not id_token:
        id_token = _extract_bearer_from_auth_header()
    if not id_token:
        logger.warning(f"Missing token for room {room_id} image request")
        abort(401, description="Missing token")

    claims = verify_id_token(id_token)
    if not claims:
        logger.warning(f"Invalid token for room {room_id} image request")
        abort(401, description="Invalid token")

    params = {}
    page = request.args.get("page")
    if page:
        try:
            page_num = int(page)
            if page_num < 1:
                logger.warning(f"Invalid page number for room {room_id}: {page}")
                abort(400, description="Page number must be positive")
            params["page"] = page_num
        except ValueError:
            logger.warning(f"Invalid page format for room {room_id}: {page}")
            abort(400, description="Invalid page format")

    url = f"{BACKEND_BASE}/rooms/{room_id}/image"
    logger.info(f"Proxying image request to {url} with params: {params}")
    
    try:
        upstream = requests.get(
            url,
            headers={"Authorization": f"Bearer {id_token}"},
            params=params,
            stream=True,
            timeout=30,
        )
    except requests.RequestException as e:
        logger.error(f"Request to backend failed: {e}")
        abort(502, description="Backend service unavailable")

    if upstream.status_code != 200:
        logger.error(f"Backend returned {upstream.status_code} for image request")
        abort(upstream.status_code)

    content_type = upstream.headers.get("Content-Type", "image/png")
    logger.info(f"Successfully proxying image for room {room_id}, content-type: {content_type}")
    return Response(upstream.iter_content(8192), content_type=content_type)

# -----------------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
