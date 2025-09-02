# Welcome to 

![Alt text](./images/HopeJAM.png)

# The Music Collaboration App

# Our Mission:

## HopeKCC is a real-time music collaboration application that allows users to share and synchronize song playlists (ChordPro format) in live sessions. It combines a FastAPI backend, Firebase authentication, a PostgreSQL database, and an asynchronous WebSocket server to enable collaborative viewing of chord sheets. Musicians can create or join virtual “rooms,” manage playlists of songs, and see changes (like song selection or page turns) refected instantly for all participants.

# Features

• Firebase Authentication: Secure sign-in integration using Firebase. All API calls are protected by Firebase ID tokens (provided as Bearer tokens). User identities (Firebase UIDs) are used for room membership and access control.

• Song Ingestion from GitHub: Automatically fetches a library of ChordPro ( .cho ) fles from a GitHub repository. A background script downloads new or updated songs, generates PDF and WebP image renditions for each song, and stores metadata in a PostgreSQL database.

• Advanced Search: Supports multiple song search methods – simple title/artist substring matching (fast ILIKE queries), trigram similarity search (via PostgreSQL pg_trgm extension for fuzzy matching), and full-text search on song titles and artists. Search results can be ranked by relevance.

• Real-Time Sync via WebSockets: A dedicated WebSocket server keeps room participants in sync.When the host selects a song or fips a page, all users in the room receive an immediate WebSocket event to update their view. Joins, leaves, and room closure events are also broadcast to participants.

• Playlist Management: Users can create personal playlists of songs, add or remove songs, and share playlists within rooms. Playlists are stored in the database and associated with user accounts.

• Room Collaboration: Low-latency room system where each room has a unique code (ID). The room host controls the playlist and song display. Participants joining a room see the current song and page and can follow along in real time.

• Robust Performance & Logging: Async architecture (FastAPI with async routes and SQLModel for async DB access). Connection pooling for the database, background tasks for heavy operations (PDF rendering, image generation), and batched WebSocket messages to handle high-frequency updates.Comprehensive logging is in place for debugging and performance monitoring.

# Setup and Installation

To run the HopeKCC server on a local machine, follow these steps:

# 1. Prerequisites

• Python 3.10+ – The application uses FastAPI and asyncio features, so a compatible Python version is required.

• PostgreSQL 13+ – A PostgreSQL database is needed for storing users, songs, playlists, and rooms.The app is designed for PostgreSQL (using the asyncpg driver); other databases are not supported.

<!-- 1 -->

• Firebase Project – You need a Firebase project for authentication. Obtain the Firebase service account JSON and base64-encode it or include it as an environment variable (see Environment Setup below).

• Git – Used to clone the repository.

• ChordPro Utility (optional) – The ingestion pipeline can use a chordpro CLI for rendering PDFs. If not present, the app falls back to an internal PDF generator. (Optional: If you want to use the ofcial ChordPro tool for higher quality formatting, install it and ensure it’s accessible.)

# 2. Clone the Repository


| git clone https://github.com/hopekcc/summer-intern-2025.git<br>cd hopekcc-summer-intern-2025  |
| --- |


(Replace with the actual repository URL if diferent.)

# 3. Environment Setup

Create a file named .env in the project root (where main.py resides). This will store confguration environment variables:

# .env (example)

DATABASE_URL=postgresql+asyncpg://&lt;USER&gt;:&lt;PASSWORD&gt;@&lt;HOST&gt;:&lt;PORT&gt;/&lt;DBNAME&gt;

FIREBASE_JSON={"type": "...", "project_id": "...", ... } # Service account

JSON

GITHUB_TOKEN=&lt;YOUR_GITHUB_TOKEN&gt; # (Optional) GitHub token to increase

API rate limits

# Other optional settings:

WS_PORT=8766 # WebSocket server port (default 8766)

# CONCURRENT_RUN=true # Set "true" to create DB indexes

concurrently on startup

# FTS_MODE=column # Options: none | expr | column (for

full-text search mode)

• DATABASE_URL: Required. The connection string for PostgreSQL. Must use 

postgresql+asyncpg:// dialect. Example: postgresql+asyncpg://user:pass@localhost:5432/hopekcc .

• FIREBASE_JSON: Required. The JSON credentials for a Firebase service account. This should be the literal JSON (string-escaped) or you can set a fle path and modify main.py to load from fle. The app uses this to initialize Firebase Admin SDK for verifying tokens.

• GITHUB_TOKEN: (Optional.) A GitHub personal access token. If provided, the song ingestion script will use it to authenticate GitHub API requests (to avoid rate limiting). The app can work without it,but may hit request limits if the songs repository is large.

• Other Optional Vars: You can customize WebSocket behavior and search indexing via env variables:

WEBSOCKET_PORT to change the WS server port.

• CONCURRENT_RUN=true to use non-blocking index creation (suitable for production migrations).

<!-- 2 -->

FTS_MODE to enable full-text search support. Options:

$"none"$  (default) – no full-text index.

◦ $"expr"$  – create a GIN index on an expression to_tsvector(title||' '||artist)

$"column$ " – add a generated ts column with combined text and index it.

After creating the .env, load it (the app uses python-dotenv to auto-load from .env on startup).

# 4. Install Dependencies

It’s recommended to use a Python virtual environment:


| python3 -m venv .venv<br>source .venv/bin/activate<br>pip install -r requirements. $t\times t$ |
| --- |


This will install all required packages (FastAPI, SQLModel, Firebase Admin SDK, Autobahn for WebSockets,etc.) as listed in requirements. $\mathrm {t}\times \mathrm {t}$  . 

# 5. Database Initialization

Ensure your PostgreSQL database is running and the DATABASE_URL is correct. The FastAPI app will automatically create tables on startup (via an async create_all ). However, you should enable the necessary PostgreSQL extensions and indexes for best performance:

• The pg_trgm extension is used for trigram similarity search. Enable it in your database: 


| CREATE EXTENSION IF NOT EXISTS pg_trgm; |
| --- |


• After the frst run (when tables are created), you can set up indexes for search:

• By running the included search index script or using the ingestion script’s option:

◦ Option 1: Run the SQL script scripts/setup/enable_pg_trgm.sql (adjust path if needed). It will create trigram GIN indexes on songs.title and songs.artist , a B-tree index on title for sorting, and a full-text ts vector column + index (if not already present).Use ENVPROD variable in the script to control concurrent index creation.

◦ Option 2: Alternatively, run the songs ingestion script with --ensure-search-infra fag (see below). For example: 


| python scripts/retrieve_songs.py --ensure-search-infra --fts-mode<br>column  |
| --- |


This will programmatically create the same indexes based on environment variables (as explained above).

<!-- 3 -->

# 6. Running the App Locally

You can start the FastAPI server with Uvicorn:


| uvicorn main:app --reload --host 0.0.0.0 --port 8080  |
| --- |


• The --reload fag is useful during development to auto-restart on code changes.

• Once running, visit http://localhost:8080/docs for the interactive Swagger API docs.

On startup, you should see log messages indicating successful DB connection, WebSocket server startup on port 8766, etc. The server will also perform a quick DB health check (if DB_STARTUP_CHECK=true in env)and log the outcome.

# 7. Initial Song Data Ingestion

The app expects song fles (ChordPro .cho format) to be present for the core functionality. After setting up, run the song ingestion script to populate the songs database and fles:


| python scripts/retrieve_songs.py |
| --- |


By default, this will: - Connect to the GitHub repository (confgured in retrieve_songs.py , default:hopekcc/song-db-chordpro ) and fetch the list of all .cho fles (including in subdirectories). -Download any .cho fles not already present in song_data/songs/ . - Generate PDFs (in song_data/songs_pdf/ ) and WebP images (in song_data/songs_img/&lt;song_id&gt;/ ) for each song using the ChordPro library or a fallback renderer. - Insert or update song entries in the database (table songs ) with metadata (title, artist, key, tempo, etc.) extracted from the fles. - Build a compressed JSON index of all songs at song_data/songs_list.json.gz for quick client loading. - (If run with --ensure-search-infra )enable the text-search infrastructure as described earlier.

Expect this script to take some time on frst run, especially if there are many songs (it generates PDFs and images for each). Progress logs will be printed to the console. Note: You should run this script periodically (or automate it via CI) to sync any new songs added to the GitHub repo.

Once songs are ingested, clients can retrieve the song list and search songs via the API.

## Deployment (Google Cloud Platform VM)

To deploy HopeKCC on a Google Cloud Platform VM (Compute Engine):

• Choose a VM Confguration: A Linux VM is recommended (e.g., Ubuntu 22.04 LTS). Ensure it has sufcient resources to handle PDF generation and concurrent WebSockets. For example, a machine with at least [fll here CPU cores, fll here GB RAM] is recommended for moderate use.

<!-- 4 -->

• System Setup: Install Python 3.10+ on the VM, along with PostgreSQL client libraries. Also, ensure Git is available to pull updates, and set up any needed frewall rules (opening port 8080 for HTTP and 8766 for WebSocket, or confgure a reverse proxy).

• Environment & Secrets: On the VM, set up the environment variables as in the .env (especially DATABASE_URL pointing to your Cloud SQL or external Postgres, and FIREBASE_JSON ). You might use Google Secret Manager or OS-level environment confgs for sensitive values.

• Running the Server: You can use the provided setup.sh script for initial installation. Copy the repository code to the VM (via git clone or CI artifact). Then:

• Run setup.sh to create the virtual environment, install requirements, initialize the database and song data, and start the Uvicorn server. (Edit the script if needed to skip certain steps or to integrate with your environment).

• Alternatively, manually follow the Setup steps above on the VM, then run uvicorn main:app (perhaps under a process manager or as a systemd service for reliability).

• Production Considerations: In production, you might run Uvicorn behind a reverse proxy like Nginx or serve via Gunicorn workers. Adjust uvicorn parameters for performance (workers, timeout) as needed. The WebSocket server runs as part of the application startup (on port 8766 by default) –ensure that port is open or forwarded if clients will connect directly, or consider reverse proxying WebSocket connections as well.

• Domain and SSL: Confgure a domain name for the VM’s IP and add SSL (for example, using Let’s Encrypt with Nginx) especially if hosting the frontend and needing secure WebSocket ( wss:// )connections.

• PostgreSQL Deployment: If using Cloud SQL for Postgres, set up the connection string accordingly and ensure the VM can reach the database (VPC or public IP with authorized networks). Run the migrations/index setup as described in Database Initialization on the production database (once).

[fll here with any specifc GCP VM instance details or frewall rules unique to your deployment].

After deployment, monitor the logs (the app logs to console and also to logs/ fles if confgured) to ensure everything starts correctly. Test the /health/db endpoint to confrm database connectivity from the VM.

## CI/CD Pipeline

The project is set up to integrate with continuous integration and deployment workfows:

• Automated Testing: A suite of Pytest tests is included (see Testing.md). In CI, these tests should run on each commit or pull request. The pytest.ini defnes markers so that slow or integration tests can be separated from fast unit tests. For example, you might run pytest -m "not slow" for quick verifcation and include slower tests in nightly builds or pre-deployment checks.

• Build Process: Since this is a Python application, the “build” mainly involves freezing dependencies and packaging the app (if using Docker or similar). In CI, you can create a Docker image with the app, or simply archive the code. The provided requirements.txt ensures reproducible environments.

• Deployment Automation: A CI pipeline can be confgured to deploy to the GCP VM after tests pass.This could be done via SSH (copying fles and restarting the service) or using a deployment service:

• Example: Use GitHub Actions to SCP the updated code to the VM and then execute a remote script to install dependencies and restart Uvicorn.

<!-- 5 -->

• If using Docker, build and push a Docker image, then pull it on the VM and run it (the VM could be running a container orchestrator or simply docker run via SSH).

• Continuous Deployment Safeguards: It’s wise to run database migrations or the song ingestion script as part of deployment. For instance, upon deployment, you might run scripts/retrieve_songs.py --sync-only to fetch any new songs without regenerating all assets, or run with --ensure-search-infra if the schema changed.

• Monitoring & Rollbacks: Ensure logging and monitoring are in place. The app provides health endpoints (e.g., GET /health/db ) which can be used by uptime checks. Use process supervision (systemd or a container restart policy) to keep the app running. In a CI/CD context, maintain backups of the database and consider versioning the song data (since song_data/ on disk could be treated as cache – it can always be re-generated by retrieve_songs.py if needed).

In summary, the CI/CD pipeline should validate code quality (linting/formatting, then run tests), package the application, and deploy it to the cloud environment with minimal downtime. (You can integrate these steps with your preferred CI service – e.g., GitHub Actions, GitLab CI, Jenkins – and insert a diagram or detailed description of the pipeline here.)

## Documentation Guide

This README provides a high-level overview and setup guide. For in-depth documentation, refer to the following:

• API.md – Complete API reference for all REST endpoints and WebSocket events (with example requests/responses and error codes).

• Pipelines.md – Detailed explanation of data fows: the song ingestion process, search indexing, real time synchronization, and the testing/deployment pipeline.

• Application.md – Architectural overview of the application, including module structure, database schema, and how the components (FastAPI, WebSocket server, Postgres, Firebase) interact.