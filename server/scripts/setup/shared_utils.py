"""
Shared utilities for the song database pipeline.
Common functions used across retrieve_songs.py and populate_db.py
"""

import os
import sys
import json
import gzip
import hashlib
import re
from typing import Dict, Optional, Tuple
from pathlib import Path

# Add server directory to path for imports
SCRIPT_DIR = Path(__file__).parent
SERVER_DIR = SCRIPT_DIR.parent.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from dotenv import load_dotenv

# ============================================================================
# ENVIRONMENT AND PATH SETUP
# ============================================================================

def setup_environment() -> bool:
    """Load environment variables from multiple possible locations"""
    env_paths = [
        SERVER_DIR / ".env",
        Path.cwd() / ".env",
        Path(".env")
    ]
    
    env_loaded = False
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded environment from: {env_path}")
            env_loaded = True
            break
    
    if not env_loaded:
        print("No .env file found. Using system environment variables only.")
    
    # Set sensible defaults for search infrastructure if not specified
    if not os.getenv("ENABLE_SEARCH_INDEXES"):
        os.environ["ENABLE_SEARCH_INDEXES"] = "true"
    if not os.getenv("CONCURRENT_INDEXES"):
        os.environ["CONCURRENT_INDEXES"] = "true"  # Default to concurrent for safety
    if not os.getenv("FTS_MODE"):
        os.environ["FTS_MODE"] = "column"  # Default to column mode
    
    return env_loaded

def get_data_paths() -> Dict[str, str]:
    """Get all data directory paths"""
    data_dir = Path(SERVER_DIR) / "song_data"
    
    paths = {
        'data_dir': str(data_dir.absolute()),
        'songs_dir': str((data_dir / "songs").absolute()),
        'songs_pdf_dir': str((data_dir / "songs_pdf").absolute()),
        'songs_img_dir': str((data_dir / "songs_img").absolute()),
        'metadata_path': str((data_dir / "songs_metadata.json").absolute()),
        'gzip_list_path': str((data_dir / "songs_list.json.gz").absolute())
    }
    
    return paths

def ensure_directories(paths: Dict[str, str]) -> bool:
    """Ensure all required directories exist with proper permissions"""
    directories = [
        paths['data_dir'],
        paths['songs_dir'], 
        paths['songs_pdf_dir'],
        paths['songs_img_dir']
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            # Test write permissions
            test_file = Path(directory) / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            print(f"Error with directory {directory}: {e}")
            return False
    
    return True

# ============================================================================
# METADATA MANAGEMENT
# ============================================================================

def read_metadata(metadata_path: str) -> Dict[str, str]:
    """Read songs metadata with error handling"""
    if not os.path.exists(metadata_path):
        return {}
    
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Warning: Failed to read metadata file {metadata_path}: {e}")
        # Try to backup corrupted file
        backup_path = f"{metadata_path}.backup"
        try:
            os.rename(metadata_path, backup_path)
            print(f"Corrupted metadata backed up to: {backup_path}")
        except Exception:
            pass
        return {}

def save_metadata(metadata: Dict[str, str], metadata_path: str) -> bool:
    """Save metadata with atomic write operation"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        
        # Write to temporary file first, then rename for atomic operation
        temp_path = f"{metadata_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        os.rename(temp_path, metadata_path)
        return True
        
    except Exception as e:
        # Clean up temp file if it exists
        temp_path = f"{metadata_path}.tmp"
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        print(f"Failed to save metadata: {e}")
        return False

def write_gzip_song_list(metadata: Dict[str, str], gzip_path: str) -> bool:
    """Write compressed song list for client bootstrap"""
    try:
        items = []
        for sid, fname in metadata.items():
            title = os.path.splitext(os.path.basename(fname))[0]
            items.append({"id": sid, "filename": fname, "title": title})
        
        # Sort numerically when possible
        def _id_key(x):
            try:
                return int(x["id"])
            except Exception:
                return x["id"]
        
        items.sort(key=_id_key)
        payload = {"count": len(items), "songs": items}
        
        with gzip.open(gzip_path, "wt", encoding="utf-8") as gz:
            json.dump(payload, gz, ensure_ascii=False)
        
        print(f"Wrote compressed song list: {gzip_path} ({len(items)} entries)")
        return True
        
    except Exception as e:
        print(f"Failed to write compressed song list: {e}")
        return False

# ============================================================================
# FILENAME UTILITIES
# ============================================================================

# Windows-safe filename helpers
INVALID_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*]')
RESERVED_BASENAMES = {
    "CON", "PRN", "AUX", "NUL",
    *{f"COM{i}" for i in range(1, 10)},
    *{f"LPT{i}" for i in range(1, 10)},
}

def sanitize_filename(name: str) -> str:
    """Make filename safe for Windows and Linux"""
    base, ext = os.path.splitext(name)
    base = INVALID_CHARS_PATTERN.sub("_", base)
    base = re.sub(r"\s+", " ", base).strip(" .")
    if not base:
        base = "untitled"
    if base.upper() in RESERVED_BASENAMES:
        base = f"_{base}"
    return f"{base}{ext or '.cho'}"

def unique_target_name(orig_name: str, existing: set) -> str:
    """Generate unique filename that doesn't conflict with existing files"""
    safe = sanitize_filename(orig_name)
    if safe not in existing:
        return safe
    
    base, ext = os.path.splitext(safe)
    suffix = hashlib.sha1(orig_name.encode("utf-8")).hexdigest()[:6]
    candidate = f"{base}--{suffix}{ext or '.cho'}"
    counter = 1
    
    while candidate in existing:
        candidate = f"{base}--{suffix}-{counter}{ext or '.cho'}"
        counter += 1
    
    return candidate

# ============================================================================
# CHORDPRO PARSING
# ============================================================================

def parse_chordpro_metadata(cho_path: str, default_title: str) -> Dict[str, Optional[str]]:
    """Extract common ChordPro tags with multi-encoding support"""
    data: Dict[str, Optional[str]] = {
        "title": None,
        "artist": None,
        "key": None,
        "tempo": None,
        "genre": None,
        "language": None,
    }
    
    # Try multiple encodings for better cross-platform compatibility
    encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
    
    for encoding in encodings:
        try:
            with open(cho_path, "r", encoding=encoding, errors="ignore") as f:
                for line in f:
                    s = line.strip()
                    if not s or not (s.startswith("{") and s.endswith("}")):
                        continue
                    inner = s[1:-1].strip()
                    if ":" not in inner:
                        continue
                    k, v = inner.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if not v:
                        continue
                    if k in ("title", "t") and not data["title"]:
                        data["title"] = v
                    elif k in ("artist", "composer", "author") and not data["artist"]:
                        data["artist"] = v
                    elif k == "key" and not data["key"]:
                        data["key"] = v
                    elif k in ("tempo", "bpm") and not data["tempo"]:
                        data["tempo"] = v
                    elif k in ("genre", "style") and not data["genre"]:
                        data["genre"] = v
                    elif k in ("language", "lang") and not data["language"]:
                        data["language"] = v
            break  # Successfully read with this encoding
        except (UnicodeDecodeError, UnicodeError):
            continue  # Try next encoding
        except Exception as e:
            print(f"⚠️  Warning: Error reading {cho_path} with {encoding}: {e}")
            break  # Other errors, stop trying
    
    if not data["title"]:
        data["title"] = default_title
    if not data["artist"]:
        data["artist"] = "Unknown"
    
    return data

# ============================================================================
# PROGRESS TRACKING
# ============================================================================

class ProgressTracker:
    """Simple progress tracking utility"""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.success_count = 0
    
    def update(self, success: bool = True, item_name: str = None):
        """Update progress counter"""
        self.current += 1
        if success:
            self.success_count += 1
        
        progress = (self.current / self.total) * 100
        status = "yes" if success else "no"
        
        if item_name:
            print(f"{status} {item_name}")
        
        print(f"Progress: {self.current}/{self.total} ({progress:.1f}%) - Success: {self.success_count}")
        
        if self.current < self.total:
            print("-" * 50)
    
    def summary(self) -> Tuple[int, int, int]:
        """Return (total, success, failed) counts"""
        failed = self.current - self.success_count
        return self.total, self.success_count, failed

# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def validate_environment() -> Tuple[bool, list]:
    """Validate environment variables and return issues"""
    issues = []
    
    # Check required environment variables
    required_vars = ["DATABASE_URL", "FIREBASE_JSON"]
    for var in required_vars:
        if not os.getenv(var):
            issues.append(f"Missing required environment variable: {var}")
    
    # Check database URL format
    db_url = os.getenv("DATABASE_URL", "")
    if db_url and not db_url.startswith("postgresql+asyncpg://"):
        issues.append(f"DATABASE_URL must use postgresql+asyncpg:// (got: {db_url.split('://')[0]}://...)")
    
    return len(issues) == 0, issues

def normalize_song_id(song_id: str) -> str:
    """Normalize song ID by removing leading zeros from numeric IDs."""
    if isinstance(song_id, str) and song_id.isdigit():
        try:
            # Convert to int and back to string to remove leading zeros
            return str(int(song_id))
        except ValueError:
            pass
    return song_id

def get_next_song_id(metadata: Dict[str, str]) -> int:
    """Get the next available song ID"""
    try:
        existing_ids = [int(k) for k in metadata.keys() if k.isdigit()]
        return max(existing_ids, default=0) + 1
    except ValueError:
        # Fallback if there are non-numeric IDs
        numeric_keys = [int(k) for k in metadata.keys() if str(k).isdigit()]
        return max(numeric_keys, default=0) + 1

def normalize_metadata_ids(metadata: Dict[str, str]) -> Dict[str, str]:
    """Normalize all song IDs in metadata dictionary."""
    normalized = {}
    for song_id, filename in metadata.items():
        normalized_id = normalize_song_id(song_id)
        normalized[normalized_id] = filename
    return normalized

# ============================================================================
# LOGGING UTILITIES
# ============================================================================

def print_phase_header(title: str, char: str = "="):
    """Print a formatted phase header"""
    print(f"\n{title}")
    print(char * len(title))

def print_section_header(title: str):
    """Print a formatted section header"""
    print(f"\n{title}")
    print("-" * len(title))

def print_summary_box(title: str, items: Dict[str, any]):
    """Print a formatted summary box"""
    print(f"\n{title}")
    print("=" * len(title))
    for key, value in items.items():
        print(f"{key}: {value}")