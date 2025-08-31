#!/usr/bin/env python3
"""
GitHub Song Synchronization Script
Pure GitHub operations - downloads .cho files and manages metadata.
No database operations or asset generation.
"""

import os
import sys
import asyncio
import argparse
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Third-party imports
import httpx

# Add server directory to path
SCRIPT_DIR = Path(__file__).parent
SERVER_DIR = SCRIPT_DIR.parent.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

# Import shared utilities
from scripts.setup.shared_utils import (
    setup_environment, get_data_paths, ensure_directories,
    read_metadata, save_metadata, write_gzip_song_list,
    unique_target_name, print_phase_header, print_section_header,
    ProgressTracker
)

# GitHub configuration
GITHUB_API_URL = "https://api.github.com/repos/hopekcc/song-db-chordpro/contents/"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# ============================================================================
# GITHUB API OPERATIONS
# ============================================================================

async def fetch_song_list_from_github() -> List[dict]:
    """Fetch complete list of .cho files from GitHub repository"""
    print_phase_header("🌐 GITHUB REPOSITORY SCAN")
    print(f"📡 GitHub API URL: {GITHUB_API_URL}")
    
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        print("🔑 Using GitHub token for authentication")
    else:
        print("⚠️  No GitHub token - using anonymous access (rate limited)")

    all_cho_files: List[dict] = []
    
    try:
        print("🔌 Establishing connection to GitHub API...")
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            print("📥 Fetching root directory contents...")
            root_response = await client.get(GITHUB_API_URL)
            root_response.raise_for_status()
            root_contents = root_response.json()
            print(f"✅ Root directory fetched ({len(root_contents)} items)")

            # Process root directory files
            root_cho = [item for item in root_contents 
                       if item.get("type") == "file" and item.get("name", "").endswith(".cho")]
            all_cho_files.extend(root_cho)
            print(f"🎵 Found {len(root_cho)} .cho files in root directory")

            # Process subdirectories
            subdirectories = [item for item in root_contents if item.get("type") == "dir"]
            print(f"📁 Found {len(subdirectories)} subdirectories to scan...")

            if subdirectories:
                print_section_header("🔍 Scanning subdirectories:")
                tasks = [client.get(subdir["url"]) for subdir in subdirectories]
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                for i, subdir_response in enumerate(responses):
                    subdir_name = subdirectories[i]["name"]
                    print(f"   📂 Processing '{subdir_name}'...", end=" ")
                    
                    if isinstance(subdir_response, Exception):
                        print(f"❌ Failed: {subdir_response}")
                        continue
                    
                    if subdir_response.status_code == 200:
                        files = subdir_response.json()
                        cho_files = [f for f in files 
                                   if f.get("type") == "file" and f.get("name", "").endswith(".cho")]
                        all_cho_files.extend(cho_files)
                        print(f"✅ {len(cho_files)} .cho files")
                    else:
                        print(f"⚠️  Status {subdir_response.status_code}")

        all_cho_files.sort(key=lambda f: f.get("name", ""))
        print(f"\n🎯 Total: {len(all_cho_files)} .cho files found across all directories")
        return all_cho_files

    except httpx.RequestError as e:
        print(f"❌ HTTP Error: Failed to fetch data from GitHub. {e}")
        return []
    except Exception as e:
        print(f"💥 Unexpected Error: {e}")
        return []

async def download_song(session: httpx.AsyncClient, file_info: dict, target_name: str, 
                       target_dir: str, semaphore: asyncio.Semaphore) -> Tuple[str, Optional[str]]:
    """Download a single song file from GitHub"""
    async with semaphore:
        orig_name = file_info["name"]
        local_path = os.path.join(target_dir, target_name)

        if os.path.exists(local_path):
            print(f"   ⏭️  Skipping '{orig_name}' (already exists)")
            return orig_name, None

        if target_name != orig_name:
            print(f"   📥 Downloading '{orig_name}' -> '{target_name}'...", end=" ")
        else:
            print(f"   📥 Downloading '{orig_name}'...", end=" ")
        
        try:
            resp = await session.get(file_info["download_url"], timeout=30.0)
            resp.raise_for_status()
            
            # Show file size
            content_length = len(resp.content)
            size_kb = content_length / 1024
            
            with open(local_path, "wb") as f:
                f.write(resp.content)
            
            print(f"✅ ({size_kb:.1f} KB)")
            return orig_name, target_name
            
        except httpx.TimeoutException:
            print(f"⏰ Timeout")
            return orig_name, None
        except httpx.RequestError as e:
            print(f"❌ Error: {e}")
            return orig_name, None
        except Exception as e:
            print(f"💥 Unexpected error: {e}")
            return orig_name, None

# ============================================================================
# FILE SYNCHRONIZATION
# ============================================================================

async def sync_github_files(paths: Dict[str, str]) -> Dict[str, str]:
    """Synchronize .cho files from GitHub to local directory"""
    print_phase_header("🔄 GITHUB FILE SYNCHRONIZATION")
    
    # Fetch GitHub file list
    github_files = await fetch_song_list_from_github()
    if not github_files:
        print("❌ No files found on GitHub or failed to fetch. Aborting sync.")
        return read_metadata(paths['metadata_path'])

    # Load existing metadata
    print_section_header("📋 Loading existing metadata")
    metadata = read_metadata(paths['metadata_path'])
    existing_filenames = set(metadata.values())
    filename_to_id = {v: k for k, v in metadata.items()}
    print(f"📊 Found {len(metadata)} existing songs in metadata")

    # Scan local directory
    print_section_header("📁 Scanning local songs directory")
    try:
        on_disk_now = set(
            fn for fn in os.listdir(paths['songs_dir'])
            if fn.lower().endswith(".cho") and os.path.isfile(os.path.join(paths['songs_dir'], fn))
        )
        print(f"📊 Found {len(on_disk_now)} .cho files on disk")
    except FileNotFoundError:
        on_disk_now = set()
        print(f"📊 Songs directory empty or doesn't exist")

    # Generate safe filenames
    print_section_header("🏷️  Generating safe filenames")
    used_names = set(existing_filenames) | set(on_disk_now)
    target_name_map: Dict[str, str] = {}
    conflicts = 0
    
    for fi in github_files:
        orig = fi["name"]
        target = unique_target_name(orig, used_names)
        target_name_map[orig] = target
        used_names.add(target)
        if target != orig:
            conflicts += 1
    
    if conflicts > 0:
        print(f"⚠️  {conflicts} files needed name sanitization")
    else:
        print(f"✅ All filenames are safe")

    # Download new files
    print_phase_header("📥 DOWNLOAD PHASE")
    
    semaphore = asyncio.Semaphore(10)
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    async with httpx.AsyncClient(headers=headers) as client:
        # Determine which files need downloading
        tasks = []
        for fi in github_files:
            target = target_name_map[fi["name"]]
            if target in existing_filenames:
                continue
            local_path = os.path.join(paths['songs_dir'], target)
            if os.path.exists(local_path):
                continue
            tasks.append(download_song(client, fi, target, paths['songs_dir'], semaphore))

        if not tasks:
            print("✅ All songs are up to date. No downloads needed.")
        else:
            print(f"🚀 Starting download of {len(tasks)} new songs...")
            results = await asyncio.gather(*tasks)
            newly_downloaded = [res for res in results if res and res[1] is not None]

            if newly_downloaded:
                print_section_header(f"📝 Registering {len(newly_downloaded)} new songs in metadata")
                
                # Get next available ID
                from scripts.setup.shared_utils import get_next_song_id
                next_id = get_next_song_id(metadata)

                for _, safe_name in newly_downloaded:
                    song_id = str(next_id)
                    # Ensure ID is normalized (remove leading zeros)
                    from scripts.setup.shared_utils import normalize_song_id
                    normalized_id = normalize_song_id(song_id)
                    metadata[normalized_id] = safe_name
                    print(f"   ✅ Registered '{safe_name}' with ID {normalized_id}")
                    next_id += 1
                
                print(f"💾 Saving metadata...")
                if save_metadata(metadata, paths['metadata_path']):
                    print(f"✅ Metadata saved")
                else:
                    print(f"❌ Failed to save metadata")
            else:
                print("⚠️  No new files were ultimately downloaded")

    # Reconcile existing files
    print_phase_header("🔍 RECONCILIATION PHASE")
    
    try:
        on_disk = {
            fn for fn in os.listdir(paths['songs_dir'])
            if fn.lower().endswith(".cho") and os.path.isfile(os.path.join(paths['songs_dir'], fn))
        }
    except FileNotFoundError:
        on_disk = set()

    meta_files = set(metadata.values())
    missing_in_meta = sorted(on_disk - meta_files)
    
    if missing_in_meta:
        print(f"🔧 Reconciling {len(missing_in_meta)} existing file(s) into metadata...")
        from scripts.setup.shared_utils import get_next_song_id
        next_id = get_next_song_id(metadata)
        
        for safe_name in missing_in_meta:
            song_id = str(next_id)
            # Ensure ID is normalized (remove leading zeros)
            from scripts.setup.shared_utils import normalize_song_id
            normalized_id = normalize_song_id(song_id)
            metadata[normalized_id] = safe_name
            print(f"   ✅ Registered existing '{safe_name}' with ID {normalized_id}")
            next_id += 1
        
        print(f"💾 Saving updated metadata...")
        save_metadata(metadata, paths['metadata_path'])
    else:
        print("✅ All local files are already in metadata")

    # Clean up orphaned files
    github_local_names = {target_name_map[f["name"]] for f in github_files}
    orphaned_files = set(filename_to_id.keys()) - github_local_names
    
    if orphaned_files:
        print(f"🗑️  Pruning {len(orphaned_files)} orphaned file(s)...")
        for file_name in sorted(orphaned_files):
            song_id_to_remove = filename_to_id.get(file_name)
            if song_id_to_remove and song_id_to_remove in metadata:
                del metadata[song_id_to_remove]
                print(f"   🗑️  Unregistered '{file_name}' (ID: {song_id_to_remove})")
            
            local_path = os.path.join(paths['songs_dir'], file_name)
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    print(f"   🗑️  Deleted local file: '{local_path}'")
                except OSError as e:
                    print(f"   ⚠️  Warning: failed to delete '{local_path}': {e}")
        
        print(f"💾 Saving cleaned metadata...")
        save_metadata(metadata, paths['metadata_path'])
    else:
        print("✅ No orphaned files to prune")

    print(f"\n✅ SYNC COMPLETE - {len(metadata)} songs ready")
    return metadata

# ============================================================================
# MAIN FUNCTION
# ============================================================================

async def main(argv=None):
    """Main function for GitHub synchronization"""
    parser = argparse.ArgumentParser(description="Synchronize .cho files from GitHub repository")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--force-download", action="store_true", help="Re-download all files even if they exist")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip cleanup of orphaned files")
    args = parser.parse_args(argv)

    print("🎵 GITHUB SONG SYNCHRONIZATION")
    print("=" * 60)
    
    # Setup environment
    if not setup_environment():
        print("⚠️  Continuing with system environment variables")
    
    # Get paths and ensure directories exist
    paths = get_data_paths()
    if not ensure_directories(paths):
        print("❌ Failed to create required directories")
        return 1
    
    print(f"📁 Data directory: {paths['data_dir']}")
    print(f"🎵 Songs directory: {paths['songs_dir']}")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    try:
        # Perform GitHub synchronization
        metadata = await sync_github_files(paths)
        
        # Generate compressed song list
        print_phase_header("🏁 FINAL STEPS")
        print(f"📦 Generating compressed song list...", end=" ")
        if write_gzip_song_list(metadata, paths['gzip_list_path']):
            print("✅")
        else:
            print("❌")
        
        # Final summary
        print_phase_header("🎯 SYNC SUMMARY")
        print(f"📊 Total songs in metadata: {len(metadata)}")
        print(f"📁 Songs directory: {paths['songs_dir']}")
        print(f"📋 Metadata file: {paths['metadata_path']}")
        print(f"📦 Compressed list: {paths['gzip_list_path']}")
        
        print(f"\n🎉 GITHUB SYNC COMPLETED SUCCESSFULLY!")
        return 0
        
    except Exception as e:
        print(f"💥 Sync failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Sync interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)