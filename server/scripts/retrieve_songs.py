import os
import shutil
import json
from git import Repo

# === PATH SETUP ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DATABASE_DIR = os.path.join(BASE_DIR, "song_database")
SONGS_DIR = os.path.join(DATABASE_DIR, "songs")
METADATA_PATH = os.path.join(DATABASE_DIR, "songs_metadata.json")

# Ensure the database directory exists before any further operations
os.makedirs(DATABASE_DIR, exist_ok=True)

GITHUB_REPO_URL = "https://github.com/asent1234/songsTest.git"

# === METADATA ===
def load_metadata():
    if not os.path.exists(METADATA_PATH):
        return {}
    try:
        with open(METADATA_PATH, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Metadata corrupted — starting fresh.")
        return {}


def save_metadata(metadata):
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)


# === GIT SYNC ===

def sync_repo():
    if not os.path.exists(SONGS_DIR):
        print("📁 Creating songs folder and cloning...")
        # DATABASE_DIR already ensured to exist
        Repo.clone_from(GITHUB_REPO_URL, SONGS_DIR)
    elif not os.path.exists(os.path.join(SONGS_DIR, ".git")):
        print("⚠️ songs/ exists but is not a git repo — replacing...")
        shutil.rmtree(SONGS_DIR)
        Repo.clone_from(GITHUB_REPO_URL, SONGS_DIR)
    else:
        print("🔄 Pulling latest changes...")
        repo = Repo(SONGS_DIR)
        repo.remotes.origin.pull()


# === PROCESS FILES ===

def process_files():
    metadata = load_metadata()
    existing_filenames = set(metadata.values())
    used_ids = [int(k) for k in metadata.keys()]
    next_id = max(used_ids, default=0) + 1
    new_files = []

    for file in os.listdir(SONGS_DIR):
        full_path = os.path.join(SONGS_DIR, file)
        if not os.path.isfile(full_path):
            continue
        if not (file.endswith(".pro") or file.endswith(".cho")):
            continue
        if file in existing_filenames:
            print(f"⏩ Skipped {file} (already registered)")
            continue

        id_str = str(next_id).zfill(4)
        metadata[id_str] = file
        new_files.append((id_str, file))
        print(f"✅ Registered {file} as {id_str}")
        next_id += 1

    save_metadata(metadata)

    if not new_files:
        print("✅ No new songs to add.")
    else:
        print(f"🎉 Added {len(new_files)} new song(s).")


# === MAIN ===
if __name__ == "__main__":
    sync_repo()
    process_files()
