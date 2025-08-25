#!/bin/bash

# Setup script for the server application
# This script initializes the environment, database, and starts the server

set -e  # Exit on any error

# --- Activate Local Perl Environment ---
# Find the script's own directory to locate the server root reliably.
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SERVER_DIR=$(dirname "$SCRIPT_DIR")
LOCAL_DEPS_DIR="$SERVER_DIR/local_deps"

# Check if the local perl environment exists
if [ -d "$LOCAL_DEPS_DIR" ]; then
    # Add the local binaries (like chordpro) to the PATH
    export PATH="$LOCAL_DEPS_DIR/bin:$PATH"
    # Source the perl environment to find libraries
    source "$LOCAL_DEPS_DIR/lib/perl5/local/lib.pm" --shell-type=bash
fi
# --- End Perl Environment Activation ---


echo "🚀 Setting up server application..."
echo "=================================="

# Determine script and server directories for robust pathing
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SERVER_DIR=$(dirname "$SCRIPT_DIR")

# Navigate to server directory
cd "$SERVER_DIR"

# 1. Virtual Environment Setup
echo "📦 Setting up virtual environment..."
if [ ! -d ".venvServer" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venvServer
fi

# Activate virtual environment
source .venvServer/bin/activate

# Install requirements
echo "Installing dependencies..."
pip3 install -r requirements.txt
echo "✅ Virtual environment ready!"

# 2. Create Directory Structure
echo ""
echo "📁 Creating directory structure..."
mkdir -p logs
mkdir -p room_database
mkdir -p song_database/songs
mkdir -p song_database/songs_pdf

# 3. Create Log Files
echo "📝 Creating log files..."
touch logs/info.log
touch logs/error.log
echo "✅ Log files created!"

# 4. Initialize Database
echo ""
echo "🗄️  Initializing database..."
python3 scripts/database_models.py
echo "✅ Database initialized!"

# 5. Run Retrieve Songs Script
echo ""
echo "🎵 Setting up songs database..."
echo "Running retrieve_songs.py..."
python3 scripts/retrieve_songs.py
echo "✅ Songs database ready!"

# 6. Start Server
echo ""
echo "🌐 Starting server..."
echo "=================================="
echo "✅ Setup completed successfully!"
echo ""
echo "Server will start on: http://localhost:8080"
echo "API docs available at: http://localhost:8080/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================="

# Start the server
nohup uvicorn main:app --host 0.0.0.0 --port 8080 &> server.log &
echo $! > server.pid 