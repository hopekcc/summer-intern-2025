import os
import json
import httpx
import asyncio

# === CONFIGURATION ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATABASE_DIR = os.path.join(BASE_DIR, "song_database")
SONGS_DIR = os.path.join(DATABASE_DIR, "songs")
METADATA_PATH = os.path.join(DATABASE_DIR, "songs_metadata.json")

# URL to the root of the GitHub API for the repository's contents
GITHUB_API_URL = "https://api.github.com/repos/hopekcc/song-db-chordpro/contents/"

# === HELPER FUNCTIONS ===

def setup_directories():
    """Ensure all necessary directories exist."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    os.makedirs(SONGS_DIR, exist_ok=True)

def load_metadata():
    """Loads song metadata from the JSON file, or returns an empty dict if not found/corrupt."""
    if not os.path.exists(METADATA_PATH):
        return {}
    try:
        with open(METADATA_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        print("⚠️ Metadata file is corrupt or unreadable. Starting fresh.")
        return {}

def save_metadata(metadata):
    """Saves the song metadata to the JSON file."""
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

async def fetch_song_list_from_github():
    """
    Fetches the list of .cho files from the GitHub repository, searching through subdirectories.
    """
    print("📡 Fetching directory list from GitHub...")
    all_cho_files = []
    
    try:
        async with httpx.AsyncClient() as client:
            # 1. Fetch the root directory contents
            root_response = await client.get(GITHUB_API_URL)
            root_response.raise_for_status()
            root_contents = root_response.json()

            # 2. Find all directories
            subdirectories = [item for item in root_contents if item.get("type") == "dir"]
            print(f"🔎 Found {len(subdirectories)} subdirectories. Fetching contents...")

            # 3. Asynchronously fetch contents of each subdirectory
            tasks = [client.get(subdir["url"]) for subdir in subdirectories]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # 4. Process responses and aggregate all .cho files
            for i, subdir_response in enumerate(responses):
                subdir_name = subdirectories[i]["name"]
                if isinstance(subdir_response, Exception):
                    print(f"❌ Failed to fetch contents for '{subdir_name}': {subdir_response}")
                    continue
                
                if subdir_response.status_code == 200:
                    files = subdir_response.json()
                    cho_files = [f for f in files if f.get("name", "").endswith(".cho")]
                    all_cho_files.extend(cho_files)
                    print(f"   - Found {len(cho_files)} .cho files in '{subdir_name}'")
                else:
                    print(f"   - Warning: Received status {subdir_response.status_code} for '{subdir_name}'")
        
        # Sort all collected files alphabetically by name for consistent ID assignment
        all_cho_files.sort(key=lambda f: f["name"])
        print(f"✅ Found a total of {len(all_cho_files)} .cho files across all directories.")
        return all_cho_files

    except httpx.RequestError as e:
        print(f"❌ HTTP Error: Failed to fetch data from GitHub. {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected Error: An error occurred while fetching the song list. {e}")
        return []


async def download_song(session: httpx.AsyncClient, file_info: dict, semaphore: asyncio.Semaphore):
    """Downloads a single song file if it doesn't already exist locally."""
    async with semaphore:
        file_name = file_info["name"]
        local_path = os.path.join(SONGS_DIR, file_name)

        if os.path.exists(local_path):
            # This case should ideally not be hit if we pre-filter
            return file_name, None

        print(f"🔽 Downloading '{file_name}'...")
        try:
            # Give each download a 30-second timeout
            response = await session.get(file_info["download_url"], timeout=30.0)
            response.raise_for_status()
            
            with open(local_path, "wb") as f:
                f.write(response.content)
            return file_name, file_name  # Return filename to indicate success
        except httpx.TimeoutException:
            print(f"❌ Timeout downloading '{file_name}'. Skipping.")
            return file_name, None
        except httpx.RequestError as e:
            print(f"❌ Failed to download '{file_name}': {e}")
            return file_name, None

async def sync_and_process_songs():
    """Main function to sync songs from GitHub and update local database."""
    github_files = await fetch_song_list_from_github()
    if not github_files:
        print("🛑 No files found on GitHub or failed to fetch. Aborting sync.")
        return

    metadata = load_metadata()
    existing_filenames = set(metadata.values())
    
    # Invert metadata for quick lookups
    title_to_id_map = {v: k for k, v in metadata.items()}
    
    # Create a semaphore to limit concurrent downloads to 10
    semaphore = asyncio.Semaphore(10)
    
    async with httpx.AsyncClient() as client:
        tasks = []
        for file_info in github_files:
            if file_info["name"] not in existing_filenames:
                tasks.append(download_song(client, file_info, semaphore))
        
        if not tasks:
            print("✅ All songs are up to date. No downloads needed.")
        else:
            print(f"⏳ Found {len(tasks)} new songs to download...")
            results = await asyncio.gather(*tasks)
            
            newly_downloaded_files = [res for res in results if res and res[1] is not None]

            if newly_downloaded_files:
                print(f"🎉 Successfully downloaded {len(newly_downloaded_files)} new song(s).")
                
                # Update metadata with the new files
                next_id = max([int(k) for k in metadata.keys()] or [0]) + 1
                for _, file_name in newly_downloaded_files:
                    song_id = f"{next_id:04d}"
                    metadata[song_id] = file_name
                    print(f"   - Registered '{file_name}' with ID {song_id}")
                    next_id += 1
                
                save_metadata(metadata)
            else:
                print("✅ No new files were ultimately downloaded after checking.")

    # Pruning logic: check for local files that are no longer in the GitHub repo
    github_filenames = {f["name"] for f in github_files}
    orphaned_files = existing_filenames - github_filenames

    if orphaned_files:
        print(f"🧹 Pruning {len(orphaned_files)} orphaned file(s)...")
        for file_name in orphaned_files:
            # Find the song ID from the filename
            song_id_to_remove = title_to_id_map.get(file_name)
            
            # Remove from metadata
            if song_id_to_remove and song_id_to_remove in metadata:
                del metadata[song_id_to_remove]
                print(f"   - Unregistered '{file_name}' (ID: {song_id_to_remove})")
            
            # Delete the local file
            local_path = os.path.join(SONGS_DIR, file_name)
            if os.path.exists(local_path):
                os.remove(local_path)
                print(f"   - Deleted local file: '{local_path}'")
        
        save_metadata(metadata)
    else:
        print("✅ No orphaned files to prune.")

# === MAIN EXECUTION ===
if __name__ == "__main__":
    setup_directories()
    asyncio.run(sync_and_process_songs())
    print("✨ Song database sync complete. ✨")
