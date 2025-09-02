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
import json
import time
from flask import (
    Flask, render_template, request, send_from_directory,
    url_for, abort, make_response, redirect, jsonify, Response  # NEW: Response for streaming
)
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import credentials, auth as admin_auth

app = Flask(__name__)

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
    return admin_auth.verify_session_cookie(session_cookie, check_revoked=True)

def current_user():
    """Return decoded user claims if a valid session cookie exists; otherwise None."""
    cookie = request.cookies.get("session")
    if not cookie:
        return None
    try:
        return verify_session_cookie(cookie)
    except Exception:
        return None

@app.context_processor
def inject_user():
    """Make `user` available in ALL templates (e.g., navbar)."""
    return {"user": current_user()}

def verify_id_token(id_token: str):
    """Verify a Firebase ID token; return claims or None on failure."""
    try:
        return admin_auth.verify_id_token(id_token)
    except Exception:
        return None

def make_room_code(n: int = 6) -> str:
    """Generate a random room number, for example DMF50P."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))

def make_slug(title: str) -> str:
    """Convert a title to safe PDF filename."""
    return re.sub(r"[^a-z0-9]", "", title.lower()) + ".pdf"

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
# Basic Routes
# -----------------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("home.html", username="Mentor", insert_text="Welcome to our demo!!!")

@app.route("/preview", methods=["GET", "POST"])
def preview():
    if request.method == "POST":
        chordpro_text = request.form.get("chordpro_text")
        return render_template("preview.html", content=chordpro_text)
    return render_template("preview.html", content=None)

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

@app.route("/songs")
def song_list():
    return render_template("songs.html")

# -----------------------------------------------------------------------------
# Playlist page
# -----------------------------------------------------------------------------
@app.route("/playlist")
def playlist():
    return render_template("playlist.html")

@app.route('/api/playlists', methods=['POST'])
def create_playlist():
    """Save a new playlist (requires authentication)"""
    try:
        # Get the authorization token from the request
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization token required'}), 401
            
        # Extract token and verify with Firebase (you may already have this logic)
        token = auth_header.split('Bearer ')[1]
        # Add your Firebase token verification here
        
        data = request.get_json()
        if not data or 'name' not in data or 'tracks' not in data:
            return jsonify({'error': 'Missing playlist name or tracks'}), 400
            
        playlist_name = data['name']
        tracks = data['tracks']
        
        # Here you would save the playlist to your database
        # For now, just return success
        playlist_id = f"playlist_{int(time.time())}"  # Simple ID generation
        
        return jsonify({
            'success': True,
            'playlist_id': playlist_id,
            'message': f'Playlist "{playlist_name}" saved with {len(tracks)} tracks'
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Failed to save playlist'}), 500

@app.route('/api/playlists', methods=['GET'])
def get_playlists():
    """Get user's playlists (requires authentication)"""
    try:
        # Get the authorization token from the request
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization token required'}), 401
            
        # Extract token and verify with Firebase
        token = auth_header.split('Bearer ')[1]
        # Add your Firebase token verification here
        
        # Here you would fetch playlists from your database
        # For now, return empty list
        playlists = []
        
        return jsonify(playlists), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch playlists'}), 500

@app.route("/dashboard")
def dashboard():
    if not current_user():
        return redirect(url_for("login_page"))
    return redirect(url_for("home"))

# LOGIN
@app.route("/login")
def login_page():
    force = request.args.get("force") == "1"
    # if not force and current_user():
    #     return redirect(url_for("home"))
    return render_template("login.html")

# SIGN IN PAGE
@app.route("/signup")
def signup():
    return render_template("signup.html")

# -----------------------------------------------------------------------------
# PDF Streaming Proxy
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
    url = f"{BACKEND_BASE}/songs/{song_id}/pdf"
    headers = {"Authorization": f"Bearer {id_token}"}
    try:
        upstream = requests.get(url, headers=headers, stream=True, timeout=30)
    except requests.RequestException:
        abort(502)
    if upstream.status_code != 200:
        abort(upstream.status_code)
    return Response(upstream.iter_content(8192), content_type="application/pdf")

# -----------------------------------------------------------------------------
# Search Routes
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
# Room Routes - Proxy to WebSocket Server
# -----------------------------------------------------------------------------
@app.route("/rooms/", methods=["POST"])
def create_room_api():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        # FastAPI requires auth; fail fast so the UI can show a clear message
        return jsonify({"error": "Authorization token required"}), 401
    try:
        r = requests.post(
            f"{BACKEND_BASE}/rooms/",
            headers={"Authorization": auth_header, "Content-Type": "application/json"},
            json={}, timeout=10
        )
        # helpful debug
        print("Create room status:", r.status_code, "body:", r.text)
        if r.status_code in (200, 201):
            data = r.json()
            code = data.get("code") or data.get("room_id") or data.get("id")
            if code:
                return jsonify({"code": code})
            return jsonify({"error": "Room created but no ID returned"}), 502
        return jsonify({"error": r.text or "Failed to create room"}), r.status_code
    except requests.RequestException as e:
        print("Room proxy error:", e)
        return jsonify({"error": "Room server unavailable"}), 502

@app.route("/rooms/create")
def create_room():
    # Render a trampoline page that does client-side create + redirect
    return render_template("create_room_trampoline.html")
    
@app.route("/rooms/<room_id>", methods=["GET"])
def room_page(room_id):
    """Render room page - let WebSocket handle all room logic"""
    return render_template("room.html", room_id=room_id)

@app.route("/rooms/join", methods=["GET", "POST"])
def join_room():
    if request.method == "POST":
        code = (request.form.get("room_code", "")).strip().upper()
        if not code:
            return render_template("join_room.html", error="Please enter the room code")
        return redirect(url_for("room_page", room_id=code))
    return render_template("join_room.html")

# Legacy route for backward compatibility
@app.route("/api/rooms", methods=["POST"])
def api_create_room():
    """Legacy AJAX endpoint - redirects to new endpoint"""
    return create_room_api()

# -----------------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)