import os
import sys
import io
import json
import argparse
import asyncio
import gzip
from typing import Optional, Tuple, Dict

# Third-party
from sqlmodel import select
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import re
import hashlib
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from PIL import Image
from dotenv import load_dotenv

# Ensure we can import runtime modules when running from server/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

# Load environment variables from server/.env so CHORDPRO_PATH and DATABASE_URL are available
load_dotenv(os.path.join(SERVER_DIR, ".env"))

# GitHub repository config for syncing .cho files
GITHUB_API_URL = "https://api.github.com/repos/hopekcc/song-db-chordpro/contents/"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Runtime database & models
from scripts.runtime.database import (
    Song,
    AsyncSessionLocal,
    create_db_and_tables_async,
    get_database_url,
    engine,
)

# Local song data paths
DATA_DIR = os.path.join(SERVER_DIR, "song_data")
SONGS_DIR = os.path.join(DATA_DIR, "songs")
SONGS_PDF_DIR = os.path.join(DATA_DIR, "songs_pdf")
SONGS_IMG_DIR = os.path.join(DATA_DIR, "songs_img")
METADATA_PATH = os.path.join(DATA_DIR, "songs_metadata.json")
GZIP_LIST_PATH = os.path.join(DATA_DIR, "songs_list.json.gz")

os.makedirs(SONGS_DIR, exist_ok=True)
os.makedirs(SONGS_PDF_DIR, exist_ok=True)
os.makedirs(SONGS_IMG_DIR, exist_ok=True)


def read_metadata() -> Dict[str, str]:
    if not os.path.exists(METADATA_PATH):
        return {}
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_metadata(metadata: Dict[str, str]) -> None:
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def write_gzip_song_list(metadata: Dict[str, str]) -> None:
    """Write songs_list.json.gz for client bootstrap."""
    items = []
    for sid, fname in metadata.items():
        title = os.path.splitext(os.path.basename(fname))[0]
        items.append({"id": sid, "filename": fname, "title": title})
    # sort numerically when possible
    def _id_key(x):
        try:
            return int(x["id"])
        except Exception:
            return x["id"]
    items.sort(key=_id_key)
    payload = {"count": len(items), "songs": items}
    with gzip.open(GZIP_LIST_PATH, "wt", encoding="utf-8") as gz:
        json.dump(payload, gz, ensure_ascii=False)
    print(f"Wrote gzipped song list: {GZIP_LIST_PATH} ({len(items)} entries)")


# === Windows-safe filename helpers ===
INVALID_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*]')
RESERVED_BASENAMES = {
    "CON", "PRN", "AUX", "NUL",
    *{f"COM{i}" for i in range(1, 10)},
    *{f"LPT{i}" for i in range(1, 10)},
}


def sanitize_filename(name: str) -> str:
    base, ext = os.path.splitext(name)
    base = INVALID_CHARS_PATTERN.sub("_", base)
    base = re.sub(r"\s+", " ", base).strip(" .")
    if not base:
        base = "untitled"
    if base.upper() in RESERVED_BASENAMES:
        base = f"_{base}"
    return f"{base}{ext or '.cho'}"


def unique_target_name(orig_name: str, existing: set) -> str:
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


async def fetch_song_list_from_github() -> list[dict]:
    print("Fetching directory list from GitHub...")
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    all_cho_files: list[dict] = []
    try:
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            root_response = await client.get(GITHUB_API_URL)
            root_response.raise_for_status()
            root_contents = root_response.json()

            root_cho = [item for item in root_contents if item.get("type") == "file" and item.get("name", "").endswith(".cho")]
            all_cho_files.extend(root_cho)

            subdirectories = [item for item in root_contents if item.get("type") == "dir"]
            print(f"Found {len(subdirectories)} subdirectories. Fetching contents...")

            tasks = [client.get(subdir["url"]) for subdir in subdirectories]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for i, subdir_response in enumerate(responses):
                subdir_name = subdirectories[i]["name"]
                if isinstance(subdir_response, Exception):
                    print(f"Failed to fetch contents for '{subdir_name}': {subdir_response}")
                    continue
                if subdir_response.status_code == 200:
                    files = subdir_response.json()
                    cho_files = [f for f in files if f.get("type") == "file" and f.get("name", "").endswith(".cho")]
                    all_cho_files.extend(cho_files)
                    print(f"   - Found {len(cho_files)} .cho files in '{subdir_name}'")
                else:
                    print(f"   - Warning: Received status {subdir_response.status_code} for '{subdir_name}'")

        all_cho_files.sort(key=lambda f: f.get("name", ""))
        print(f"Found a total of {len(all_cho_files)} .cho files across all directories.")
        return all_cho_files

    except httpx.RequestError as e:
        print(f"HTTP Error: Failed to fetch data from GitHub. {e}")
        return []
    except Exception as e:
        print(f"Unexpected Error: An error occurred while fetching the song list. {e}")
        return []


async def download_song(session: httpx.AsyncClient, file_info: dict, target_name: str, semaphore: asyncio.Semaphore) -> tuple[str, Optional[str]]:
    async with semaphore:
        orig_name = file_info["name"]
        safe_name = target_name
        local_path = os.path.join(SONGS_DIR, safe_name)

        if os.path.exists(local_path):
            return orig_name, None

        if safe_name != orig_name:
            print(f"Downloading '{orig_name}' -> '{safe_name}'...")
        else:
            print(f"Downloading '{orig_name}'...")
        try:
            resp = await session.get(file_info["download_url"], timeout=30.0)
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(resp.content)
            return orig_name, safe_name
        except httpx.TimeoutException:
            print(f"Timeout downloading '{orig_name}'. Skipping.")
            return orig_name, None
        except httpx.RequestError as e:
            print(f"Failed to download '{orig_name}': {e}")
            return orig_name, None


async def sync_github_and_update_metadata() -> Dict[str, str]:
    """Sync .cho files from GitHub into SONGS_DIR and update songs_metadata.json."""
    github_files = await fetch_song_list_from_github()
    if not github_files:
        print("No files found on GitHub or failed to fetch. Aborting sync.")
        return read_metadata()

    metadata = read_metadata()
    existing_filenames = set(metadata.values())
    filename_to_id = {v: k for k, v in metadata.items()}

    try:
        on_disk_now = set(
            fn for fn in os.listdir(SONGS_DIR)
            if fn.lower().endswith(".cho") and os.path.isfile(os.path.join(SONGS_DIR, fn))
        )
    except FileNotFoundError:
        on_disk_now = set()
    used_names = set(existing_filenames) | set(on_disk_now)
    target_name_map: Dict[str, str] = {}
    for fi in github_files:
        orig = fi["name"]
        target = unique_target_name(orig, used_names)
        target_name_map[orig] = target
        used_names.add(target)

    semaphore = asyncio.Semaphore(10)
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    async with httpx.AsyncClient(headers=headers) as client:
        tasks = []
        for fi in github_files:
            target = target_name_map[fi["name"]]
            if target in existing_filenames:
                continue
            local_path = os.path.join(SONGS_DIR, target)
            if os.path.exists(local_path):
                continue
            tasks.append(download_song(client, fi, target, semaphore))

        if not tasks:
            print("All songs are up to date. No downloads needed.")
        else:
            print(f"Found {len(tasks)} new songs to download...")
            results = await asyncio.gather(*tasks)
            newly_downloaded = [res for res in results if res and res[1] is not None]

            if newly_downloaded:
                print(f"Successfully downloaded {len(newly_downloaded)} new song(s).")
                try:
                    next_id = max([int(k) for k in metadata.keys()] or [0]) + 1
                except ValueError:
                    numeric_keys = [int(k) for k in metadata.keys() if str(k).isdigit()]
                    next_id = (max(numeric_keys) if numeric_keys else 0) + 1

                for _, safe_name in newly_downloaded:
                    song_id = str(next_id)
                    metadata[song_id] = safe_name
                    print(f"   - Registered '{safe_name}' with ID {song_id}")
                    next_id += 1
                save_metadata(metadata)
            else:
                print("No new files were ultimately downloaded after checking.")

    try:
        on_disk = {
            fn for fn in os.listdir(SONGS_DIR)
            if fn.lower().endswith(".cho") and os.path.isfile(os.path.join(SONGS_DIR, fn))
        }
    except FileNotFoundError:
        on_disk = set()

    meta_files = set(metadata.values())
    missing_in_meta = sorted(on_disk - meta_files)
    if missing_in_meta:
        print(f"Reconciling {len(missing_in_meta)} existing file(s) into metadata...")
        try:
            next_id = max([int(k) for k in metadata.keys()] or [0]) + 1
        except ValueError:
            numeric_keys = [int(k) for k in metadata.keys() if str(k).isdigit()]
            next_id = (max(numeric_keys) if numeric_keys else 0) + 1
        for safe_name in missing_in_meta:
            song_id = str(next_id)
            metadata[song_id] = safe_name
            print(f"   - Registered existing '{safe_name}' with ID {song_id}")
            next_id += 1
        save_metadata(metadata)

    github_local_names = {target_name_map[f["name"]] for f in github_files}
    orphaned_files = set(filename_to_id.keys()) - github_local_names
    if orphaned_files:
        print(f"Pruning {len(orphaned_files)} orphaned file(s)...")
        for file_name in sorted(orphaned_files):
            song_id_to_remove = filename_to_id.get(file_name)
            if song_id_to_remove and song_id_to_remove in metadata:
                del metadata[song_id_to_remove]
                print(f"   - Unregistered '{file_name}' (ID: {song_id_to_remove})")
            local_path = os.path.join(SONGS_DIR, file_name)
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    print(f"   - Deleted local file: '{local_path}'")
                except OSError as e:
                    print(f"   - Warning: failed to delete '{local_path}': {e}")
        save_metadata(metadata)
    else:
        print("No orphaned files to prune.")

    return metadata


async def ensure_search_infra_from_env() -> None:
    """Enable pg_trgm and create trigram GIN indexes, and optional FTS infra.

    Controlled by env var 'concurrnetrun' (also accepts 'CONCURRENTRUN'/'CONCURRENT_RUN').
    - True: use CREATE INDEX CONCURRENTLY (non-blocking; must run outside txn)
    - False: use normal CREATE INDEX (may block; OK for local dev)

    Optional FTS mode via env 'FTS_MODE' in {none, expr, column}:
    - expr: expression GIN index on to_tsvector('simple', title||' '||artist)
    - column: add 'ts' tsvector column, populate, and GIN index (no triggers)
    """
    # Resolve boolean from env (default False)
    raw = os.getenv("concurrnetrun", os.getenv("CONCURRENTRUN", os.getenv("CONCURRENT_RUN", "false")))
    concurrent = str(raw).strip().lower() in {"1", "true", "t", "yes", "y", "on"}

    enable_ext = "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
    idx_title = (
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_songs_title_trgm ON songs USING gin (title gin_trgm_ops);"
        if concurrent
        else "CREATE INDEX IF NOT EXISTS idx_songs_title_trgm ON songs USING gin (title gin_trgm_ops);"
    )
    idx_artist = (
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_songs_artist_trgm ON songs USING gin (artist gin_trgm_ops);"
        if concurrent
        else "CREATE INDEX IF NOT EXISTS idx_songs_artist_trgm ON songs USING gin (artist gin_trgm_ops);"
    )
    fts_mode = (os.getenv("FTS_MODE", "none").strip().lower())
    expr_idx = (
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_songs_fts_expr ON songs USING gin (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(artist,'')));"
        if concurrent
        else "CREATE INDEX IF NOT EXISTS idx_songs_fts_expr ON songs USING gin (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(artist,'')));"
    )
    col_add = "ALTER TABLE songs ADD COLUMN IF NOT EXISTS ts tsvector;"
    col_populate = "UPDATE songs SET ts = to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(artist,''));"
    col_idx = (
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_songs_fts ON songs USING gin (ts);"
        if concurrent
        else "CREATE INDEX IF NOT EXISTS idx_songs_fts ON songs USING gin (ts);"
    )

    # Run outside transaction for CONCURRENTLY; harmless for non-concurrent too
    async with engine.connect() as conn:
        ac = conn.execution_options(isolation_level="AUTOCOMMIT")
        base_stmts = [enable_ext, idx_title, idx_artist]
        if fts_mode == "expr":
            base_stmts.append(expr_idx)
        elif fts_mode == "column":
            base_stmts.extend([col_add, col_populate, col_idx])
        for stmt in base_stmts:
            try:
                await ac.execute(text(stmt))
                if "CREATE INDEX" in stmt:
                    print(f"Ran index create: {stmt.split('ON')[0].strip()}")
                elif stmt.startswith("ALTER TABLE"):
                    print("Ensured tsvector column exists")
                elif stmt.startswith("UPDATE songs SET ts"):
                    print("Populated tsvector column")
                else:
                    print("Ensured pg_trgm extension")
            except Exception as e:
                print(f"Statement failed/skipped: {e}")


def parse_chordpro_metadata(cho_path: str, default_title: str) -> Dict[str, Optional[str]]:
    """Extract common ChordPro tags into a dict.
    Keys: title, artist, key, tempo, genre, language
    """
    data: Dict[str, Optional[str]] = {
        "title": None,
        "artist": None,
        "key": None,
        "tempo": None,
        "genre": None,
        "language": None,
    }
    try:
        with open(cho_path, "r", encoding="utf-8", errors="ignore") as f:
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
    except Exception:
        pass
    if not data["title"]:
        data["title"] = default_title
    if not data["artist"]:
        data["artist"] = "Unknown"
    return data


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def render_pdf_from_text(text: str, pdf_path: str) -> int:
    """Render simple monospaced PDF from text. Returns page count (fallback)."""
    ensure_dir(os.path.dirname(pdf_path))

    # Use built-in Courier font
    page_width, page_height = letter
    margin = 0.75 * inch
    leading = 12  # line height
    font_name = "Courier"
    font_size = 10

    from reportlab.pdfgen import canvas as _canvas
    c = _canvas.Canvas(pdf_path, pagesize=letter)
    c.setTitle(os.path.splitext(os.path.basename(pdf_path))[0])
    c.setFont(font_name, font_size)

    max_width = page_width - 2 * margin
    x = margin
    y = page_height - margin

    # naive wrap by characters
    avg_char_width = 0.6 * font_size
    max_chars_per_line = max(10, int(max_width / avg_char_width))

    def wrap_line(line: str):
        if len(line) <= max_chars_per_line:
            return [line]
        out = []
        start = 0
        while start < len(line):
            out.append(line[start:start + max_chars_per_line])
            start += max_chars_per_line
        return out

    page_count = 1
    for raw_line in text.splitlines():
        for seg in wrap_line(raw_line.rstrip("\n")):
            if y - leading < margin:
                c.showPage()
                c.setFont(font_name, font_size)
                y = page_height - margin
                page_count += 1
            c.drawString(x, y, seg)
            y -= leading
        if y - leading < margin:
            c.showPage()
            c.setFont(font_name, font_size)
            y = page_height - margin
            page_count += 1
        y -= leading

    c.save()
    return page_count


async def render_pdf_with_chordpro_or_fallback(cho_path: str, pdf_path: str, content: str) -> int:
    """Try rendering via ChordPro (CHORDPRO_PATH). Fallback to simple renderer."""
    exe = os.getenv("CHORDPRO_PATH")
    if exe and os.path.exists(exe):
        ensure_dir(os.path.dirname(pdf_path))
        try:
            proc = await asyncio.create_subprocess_exec(
                exe,
                "-o",
                pdf_path,
                cho_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await proc.communicate()
            if proc.returncode == 0 and os.path.exists(pdf_path):
                try:
                    with fitz.open(pdf_path) as doc:
                        return doc.page_count
                except Exception:
                    pass
            else:
                print(f"ChordPro failed ({proc.returncode}). Falling back. stderr: {err.decode(errors='ignore')[:200]}")
        except Exception as e:
            print(f"Failed to run ChordPro at {exe}: {e}. Falling back renderer.")
    # Fallback
    return await asyncio.to_thread(render_pdf_from_text, content, pdf_path)


def render_webp_from_pdf(pdf_path: str, out_dir: str, scale: float = 2.0, quality: int = 80):
    ensure_dir(out_dir)
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            out_path = os.path.join(out_dir, f"page_{i}.webp")
            img.save(out_path, format="WEBP", quality=quality)


async def reset_songs_table(session: AsyncSession):
    # Clear only the songs table; do not touch room-related tables.
    await session.execute(select(Song))  # ensure table exists via metadata linkage
    await session.execute(text("DELETE FROM songs"))


async def upsert_song(
    session: AsyncSession,
    song_id: str,
    *,
    title: str,
    artist: Optional[str],
    filename: Optional[str],
    page_count: int,
    key: Optional[str] = None,
    tempo: Optional[str] = None,
    genre: Optional[str] = None,
    language: Optional[str] = None,
):
    # Upsert logic: fetch, then update or insert
    res = await session.execute(select(Song).where(Song.id == song_id))
    existing = res.scalars().first()
    if existing:
        existing.title = title
        existing.artist = artist
        existing.filename = filename
        existing.page_count = page_count
        existing.key = key
        existing.tempo = tempo
        existing.genre = genre
        if language:
            existing.language = language
    else:
        obj = Song(
            id=song_id,
            title=title,
            artist=artist,
            filename=filename,
            page_count=page_count,
            key=key,
            tempo=tempo,
            genre=genre,
            language=language,
        )
        session.add(obj)


async def process_one_song(session: AsyncSession, song_id: str, filename: str, regen_assets: bool = False) -> Tuple[str, bool]:
    cho_path = os.path.join(SONGS_DIR, filename)
    if not os.path.exists(cho_path):
        return song_id, False

    default_title = os.path.splitext(filename)[0]
    md = parse_chordpro_metadata(cho_path, default_title)
    title = md.get("title") or default_title
    artist = md.get("artist")
    key_meta = md.get("key")
    tempo_meta = md.get("tempo")
    genre_meta = md.get("genre")
    language_meta = md.get("language")

    # Paths
    pdf_dir = SONGS_PDF_DIR
    img_dir = os.path.join(SONGS_IMG_DIR, song_id)
    pdf_path = os.path.join(pdf_dir, f"{song_id}.pdf")

    need_pdf = regen_assets or not os.path.exists(pdf_path)

    # Read content
    with open(cho_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    page_count: Optional[int] = None
    if need_pdf:
        page_count = await render_pdf_with_chordpro_or_fallback(cho_path, pdf_path, content)
    else:
        try:
            with fitz.open(pdf_path) as doc:
                page_count = doc.page_count
        except Exception:
            page_count = await render_pdf_with_chordpro_or_fallback(cho_path, pdf_path, content)

    # Generate WebP images if needed
    need_images = regen_assets or not (os.path.isdir(img_dir) and any(fn.endswith('.webp') for fn in os.listdir(img_dir)))
    if need_images:
        await asyncio.to_thread(render_webp_from_pdf, pdf_path, img_dir)

    await upsert_song(
        session,
        song_id,
        title=title,
        artist=artist,
        filename=filename,
        page_count=int(page_count or 0),
        key=key_meta,
        tempo=tempo_meta,
        genre=genre_meta,
        language=language_meta,
    )
    return song_id, True


async def main(argv=None):
    parser = argparse.ArgumentParser(description="Retrieve songs: GitHub sync, optional reset, generate PDFs/WebPs via ChordPro, and upsert into DB.")
    parser.add_argument("--reset-songs", action="store_true", help="Delete all rows from songs table before upsert.")
    parser.add_argument("--only-reset", action="store_true", help="Only reset songs table and exit (no asset generation).")
    parser.add_argument("--regen-assets", action="store_true", help="Force regenerate PDF and WebP assets.")
    parser.add_argument("--concurrency", type=int, default=6, help="Concurrent tasks for asset generation.")
    parser.add_argument("--require-postgres", action="store_true", help="Abort if DATABASE_URL is not PostgreSQL.")
    parser.add_argument("--no-sync", action="store_true", help="Skip GitHub sync step.")
    parser.add_argument("--sync-only", action="store_true", help="Only perform GitHub sync and update metadata/gz, then exit.")
    parser.add_argument("--ensure-search-infra", action="store_true", help="Ensure pg_trgm and search indexes exist (uses CONCURRENT_RUN env unless --allow-blocking is set). Optional --fts-mode controls FTS infra.")
    parser.add_argument("--allow-blocking", action="store_true", help="Allow blocking index creation (sets CONCURRENT_RUN=false for this run).")
    parser.add_argument("--fts-mode", choices=["none", "expr", "column"], default=None, help="FTS mode: expression index, tsvector column, or none.")
    args = parser.parse_args(argv)

    db_url = get_database_url()
    if args.require_postgres and not db_url.startswith("postgresql+asyncpg://"):
        print(f"DATABASE_URL is not PostgreSQL (current: {db_url}). Aborting due to --require-postgres.")
        return 2

    await create_db_and_tables_async()

    # Optional: ensure search infra
    if args.ensure_search_infra:
        if args.allow_blocking:
            os.environ["CONCURRENT_RUN"] = "false"
        if args.fts_mode is not None:
            os.environ["FTS_MODE"] = args.fts_mode
        await ensure_search_infra_from_env()

    # Allow quick reset for DB viewer verification
    async with AsyncSessionLocal() as session:
        if args.reset_songs or args.only_reset:
            print("Clearing songs table...")
            await reset_songs_table(session)
            await session.commit()
            print("Songs table cleared.")
            if args.only_reset:
                return 0

    # Sync from GitHub unless disabled
    if not args.no_sync:
        metadata = await sync_github_and_update_metadata()
        if args.sync_only:
            write_gzip_song_list(metadata)
            return 0

    metadata = read_metadata()
    if not metadata:
        print("No songs_metadata.json found or it's empty. Run the GitHub sync first.")
        return 1

    # Create one session for batching
    async with AsyncSessionLocal() as session:
        # Build work list
        items = sorted(metadata.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else kv[0])
        sem = asyncio.Semaphore(max(1, args.concurrency))

        async def worker(song_id: str, filename: str):
            async with sem:
                try:
                    _, ok = await process_one_song(session, song_id, filename, regen_assets=args.regen_assets)
                    return ok
                except Exception as e:
                    print(f"Failed processing {song_id}:{filename} -> {e}")
                    return False

        tasks = [asyncio.create_task(worker(sid, fn)) for sid, fn in items]
        results = await asyncio.gather(*tasks)
        await session.commit()

    ok_count = sum(1 for r in results if r)
    print(f"Completed upsert for {ok_count}/{len(results)} songs.")
    # Always refresh gzipped list at the end so this one script does everything
    write_gzip_song_list(metadata)
    return 0


if __name__ == "__main__":
    try:
        code = asyncio.run(main())
    except KeyboardInterrupt:
        code = 130
    sys.exit(code)
