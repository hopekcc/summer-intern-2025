
# app.py
# -----------------------------------------------------------------------------
# Flask app for the HOPEKCC Chord Pro Tool
# - Routes (home, preview, view PDF, search by artist/title, rooms, etc.)
# - Firebase Admin session handling (exchange ID token -> session cookie)
# - Helpers to get current user and protect routes
# - Logout returns to homepage; dashboard page not required
# -----------------------------------------------------------------------------

import os
import re  # regex
import datetime

from flask import (
    Flask, render_template, request, send_from_directory,
    url_for, abort, make_response, redirect
)
from werkzeug.utils import secure_filename

import firebase_admin
from firebase_admin import credentials, auth as admin_auth

app = Flask(__name__)

# -----------------------------------------------------------------------------
# Firebase Admin initialization
# Place your service account JSON in the project root and DO NOT commit it.
# Example filename: serviceAccountKey.json
# -----------------------------------------------------------------------------
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def verify_session_cookie(session_cookie: str):
    """
    Verify a Firebase session cookie.
    Returns decoded claims on success; raises on failure.
    """
    return admin_auth.verify_session_cookie(session_cookie, check_revoked=True)

def current_user():
    """
    Return decoded user claims if a valid session cookie exists; otherwise None.
    """
    cookie = request.cookies.get("session")
    if not cookie:
        return None
    try:
        return verify_session_cookie(cookie)
    except Exception:
        return None

@app.context_processor
def inject_user():
    """
    Make `user` available in ALL templates (e.g., navbar) without manually passing it.
    """
    return {"user": current_user()}

# -----------------------------------------------------------------------------
# Session routes (front-end posts Firebase ID token here after login)
# -----------------------------------------------------------------------------
@app.route("/sessionLogin", methods=["POST"])
def session_login():
    """
    Exchange a Firebase ID token for a secure session cookie.
    Front-end should POST JSON: { "idToken": "<ID_TOKEN>" }
    """
    data = request.get_json(silent=True) or {}
    id_token = data.get("idToken")
    if not id_token:
        return ("Missing idToken", 400)

    expires_in = datetime.timedelta(days=5)  # session lifetime
    try:
        session_cookie = admin_auth.create_session_cookie(id_token, expires_in=expires_in)
    except Exception as e:
        return (f"Failed to create session cookie: {e}", 401)

    resp = make_response("ok")
    # For local development over http, secure=False; in production (HTTPS) set secure=True.
    resp.set_cookie(
        "session",
        session_cookie,
        max_age=int(expires_in.total_seconds()),
        httponly=True,
        secure=False,   # CHANGE TO True when deployed behind HTTPS
        samesite="Lax"
    )
    return resp

@app.route("/logout")
def logout():
    """
    Clear the session cookie and redirect to the HOME page.
    """
    resp = make_response(redirect(url_for("home")))
    resp.delete_cookie("session")
    return resp

# -----------------------------------------------------------------------------
# PDF/Preview config
# -----------------------------------------------------------------------------
PDF_FOLDER = os.path.join(app.root_path, "static", "pdfs")
app.config["PDF_FOLDER"] = PDF_FOLDER

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/")
def home():
    """
    Public home page.
    """
    return render_template("home.html", username="Mentor", insert_text="Welcome to our demo!!!")

# CHORDPRO PREVIEW
@app.route("/preview", methods=["GET", "POST"])
def preview():
    """
    Simple page to preview ChordPro text.
    """
    if request.method == "POST":
        chordpro_text = request.form.get("chordpro_text")
        return render_template("preview.html", content=chordpro_text)
    return render_template("preview.html", content=None)

# CHORDPRO PDF VIEWER (template wrapper)
@app.route("/view/<path:filename>")
def view_pdf(filename):
    """
    Render a simple template that embeds the PDF (served by /pdfs/<filename>).
    """
    filename = secure_filename(filename)
    file_path = os.path.join(app.config["PDF_FOLDER"], filename)
    if not os.path.exists(file_path):
        abort(404)
    return render_template("view.html", filename=filename)

# Utility to create a slug file name for PDFs from song titles
def make_slug(title: str) -> str:
    """
    Convert a title to a safe PDF filename: lowercase, keep a-z0-9, remove others.
    """
    return re.sub(r"[^a-z0-9]", "", title.lower()) + ".pdf"

# RAW PDF serving (used by the viewer)
@app.route("/pdfs/<path:filename>")
def serve_pdf(filename):
    """
    Serve a PDF file from static/pdfs for embedding/downloading.
    """
    return send_from_directory(app.config["PDF_FOLDER"], filename)

# ARTIST SEARCH
@app.route("/search_artist", methods=["GET"])
def search_artist():
    """
    Fake artist list filtered by first letter. Replace with real DB later.
    """
    artists = [
        "Andy", "Brandon", "Caleb", "Drake",
        "Edward", "Fred", "Grayson", "Humza",
        "Ismael", "John", "Kush", "Lawson",
        "Michelle", "Nick", "Owen", "Peter",
        "John", "Ryan", "Sophie", "Trevor",
        "Uno", "Vivian", "William", "Xanthos",
        "Yerson", "Zachery"
    ]

    letter = request.args.get("letter", "A").upper()
    filtered = [artist for artist in artists if artist.upper().startswith(letter)]
    return render_template("search_artist.html", letter=letter, artists=filtered)

# TITLE SEARCH
@app.route("/search_title", methods=["GET", "POST"])
def search_title():
    """
    Fake title search that maps to /view/<slug>. Replace with DB search later.
    """
    all_songs = [
        "Finger Family Song",
        "Jingle Bells",
        "London Bridge is Falling Down",
        "Old McDonald Had A Farm",
        "Thomas and Friends Theme Song",
        "Fix You",
        "Believer",
        "Blinding Lights",
        "Starboy",
        "Love Story",
        "Love Me Like You Do",
        "Neveda",
    ]

    results = []
    keyword = ""

    if request.method == "POST":
        keyword = (request.form.get("keyword", "")).strip().lower()
        for song in all_songs:
            if keyword in song.lower():
                filename = make_slug(song)
                pdf_url = url_for("view_pdf", filename=filename)  # builds "/view/<slug>.pdf"
                results.append({"title": song, "pdf_url": pdf_url})

    return render_template("search_title.html", keyword=keyword, results=results)

# CREATE ROOM
@app.route("/rooms/create")
def create_room():
    return render_template("create_room.html")

# JOIN ROOM
@app.route("/rooms/join")
def join_room():
    return render_template("join_room.html")

# LOGIN PAGE
@app.route("/login")
def login_page():
    force = request.args.get("force") == "1"
    if not force and current_user():
        return redirect(url_for("home"))
    return render_template("login.html")

# ROOM PAGE (stub demo)
@app.route("/rooms/<room_id>")
def room_page(room_id):
    """
    Render live-room UI (stub).
    """
    return render_template("room.html", room_id=room_id)

# SONG LIST PAGE
@app.route("/songs")
def song_list():
    return render_template("songs.html")

# Optional protected page (kept for compatibility). You can delete this route if unused.
@app.route("/dashboard")
def dashboard():
    """
    If you ever visit /dashboard:
    - If NOT logged in -> go to login page
    - If logged in -> send to home (since we don't use dashboard.html anymore)
    """
    if not current_user():
        return redirect(url_for("login_page"))
    return redirect(url_for("home"))

# -----------------------------------------------------------------------------
# Run (GCP-friendly)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # On GCP, PORT is usually provided; default to 8080.
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
