#!/usr/bin/env python3
"""
Database Population Script
Processes local .cho files and populates the database with songs, PDFs, and images.
No GitHub operations - works with existing local files.
"""

import os
import sys
import asyncio
import argparse
import io
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path

# Third-party imports
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from PIL import Image

# Add server directory to path
SCRIPT_DIR = Path(__file__).parent
SERVER_DIR = SCRIPT_DIR.parent.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

# Import shared utilities
from scripts.setup.shared_utils import (
    setup_environment, get_data_paths, ensure_directories,
    read_metadata, parse_chordpro_metadata,
    print_phase_header, print_section_header, ProgressTracker,
    validate_environment
)

# Database imports
from scripts.runtime.database import (
    Song, AsyncSessionLocal, create_db_and_tables_async,
    get_database_url, engine
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

# ============================================================================
# PDF GENERATION
# ============================================================================

def render_pdf_from_text(text: str, pdf_path: str) -> int:
    """Render simple monospaced PDF from text. Returns page count."""
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Use built-in Courier font
    page_width, page_height = letter
    margin = 0.75 * inch
    leading = 12  # line height
    font_name = "Courier"
    font_size = 10

    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setTitle(os.path.splitext(os.path.basename(pdf_path))[0])
    c.setFont(font_name, font_size)

    max_width = page_width - 2 * margin
    x = margin
    y = page_height - margin

    # Naive wrap by characters
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
    song_name = os.path.basename(cho_path)
    
    if exe and os.path.exists(exe):
        print(f"      🎼 Using ChordPro to render PDF...", end=" ")
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        try:
            proc = await asyncio.create_subprocess_exec(
                exe, "-o", pdf_path, cho_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await proc.communicate()
            if proc.returncode == 0 and os.path.exists(pdf_path):
                try:
                    with fitz.open(pdf_path) as doc:
                        page_count = doc.page_count
                        print(f"✅ ({page_count} pages)")
                        return page_count
                except Exception as e:
                    print(f"❌ PDF validation failed: {e}")
            else:
                stderr_msg = err.decode(errors='ignore')[:200] if err else "No error output"
                print(f"❌ ChordPro failed (code {proc.returncode})")
                print(f"         Error: {stderr_msg}")
                print(f"      🔄 Falling back to simple renderer...")
        except Exception as e:
            print(f"❌ Failed to run ChordPro: {e}")
            print(f"      🔄 Falling back to simple renderer...")
    else:
        if exe:
            print(f"      ⚠️  ChordPro not found at {exe}, using fallback renderer...", end=" ")
        else:
            print(f"      📝 Using simple text renderer...", end=" ")
    
    # Fallback renderer
    try:
        page_count = await asyncio.to_thread(render_pdf_from_text, content, pdf_path)
        print(f"✅ ({page_count} pages)")
        return page_count
    except Exception as e:
        print(f"❌ Fallback renderer failed: {e}")
        return 1  # Default to 1 page if everything fails

# ============================================================================
# IMAGE GENERATION
# ============================================================================

def render_webp_from_pdf(pdf_path: str, out_dir: str, scale: float = 2.0, quality: int = 80):
    """Generate WebP images from PDF pages"""
    os.makedirs(out_dir, exist_ok=True)
    
    try:
        with fitz.open(pdf_path) as doc:
            page_count = doc.page_count
            print(f"      🖼️  Generating {page_count} WebP images...", end=" ")
            
            for i, page in enumerate(doc, start=1):
                mat = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                out_path = os.path.join(out_dir, f"page_{i}.webp")
                img.save(out_path, format="WEBP", quality=quality)
            
            print(f"✅")
            
    except Exception as e:
        print(f"❌ Image generation failed: {e}")
        raise

# ============================================================================
# SEARCH INFRASTRUCTURE SETUP
# ============================================================================

async def setup_search_infrastructure() -> bool:
    """Set up PostgreSQL search extensions and indexes"""
    db_url = get_database_url()
    if not db_url.startswith("postgresql"):
        print("⏭️  Skipping search infrastructure - not using PostgreSQL")
        return True
    
    # Check if search infrastructure should be enabled
    enable_search = os.getenv("ENABLE_SEARCH_INDEXES", "true").lower() in ("1", "true", "yes", "on")
    if not enable_search:
        print("⏭️  Skipping search infrastructure - disabled by ENABLE_SEARCH_INDEXES")
        return True
    
    print_section_header("🔍 Setting up search infrastructure")
    
    # Configuration from environment
    concurrent = os.getenv("CONCURRENT_INDEXES", "true").lower() in ("1", "true", "yes", "on")
    fts_mode = os.getenv("FTS_MODE", "column").lower()
    
    print(f"🔧 Configuration:")
    print(f"   - Concurrent indexes: {concurrent}")
    print(f"   - FTS mode: {fts_mode}")
    
    # SQL statements
    enable_ext = "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
    
    # Index creation statements
    if concurrent:
        idx_title = "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_songs_title_trgm ON songs USING gin (title gin_trgm_ops);"
        idx_artist = "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_songs_artist_trgm ON songs USING gin (artist gin_trgm_ops);"
        idx_title_btree = "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_songs_title_btree ON songs (title);"
    else:
        idx_title = "CREATE INDEX IF NOT EXISTS idx_songs_title_trgm ON songs USING gin (title gin_trgm_ops);"
        idx_artist = "CREATE INDEX IF NOT EXISTS idx_songs_artist_trgm ON songs USING gin (artist gin_trgm_ops);"
        idx_title_btree = "CREATE INDEX IF NOT EXISTS idx_songs_title_btree ON songs (title);"
    
    # FTS statements
    fts_statements = []
    if fts_mode == "expr":
        if concurrent:
            fts_statements.append("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_songs_fts_expr ON songs USING gin (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(artist,'')));")
        else:
            fts_statements.append("CREATE INDEX IF NOT EXISTS idx_songs_fts_expr ON songs USING gin (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(artist,'')));")
    elif fts_mode == "column":
        fts_statements.extend([
            "ALTER TABLE songs ADD COLUMN IF NOT EXISTS ts tsvector GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(artist,''))) STORED;",
        ])
        if concurrent:
            fts_statements.append("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_songs_ts_gin ON songs USING gin (ts);")
        else:
            fts_statements.append("CREATE INDEX IF NOT EXISTS idx_songs_ts_gin ON songs USING gin (ts);")
    
    # Execute statements
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Use autocommit connection for CONCURRENTLY operations
            async with engine.connect() as conn:
                ac = conn.execution_options(isolation_level="AUTOCOMMIT")
                
                # Enable extension
                print(f"   🔌 Enabling pg_trgm extension...", end=" ")
                try:
                    await ac.execute(text(enable_ext))
                    print("✅")
                except Exception as e:
                    print(f"❌ {e}")
                    return False
                
                # Create trigram indexes
                print(f"   📊 Creating trigram indexes...")
                for stmt, desc in [
                    (idx_title, "title trigram index"),
                    (idx_artist, "artist trigram index"),
                    (idx_title_btree, "title B-tree index")
                ]:
                    print(f"      - {desc}...", end=" ")
                    try:
                        await ac.execute(text(stmt))
                        print("✅")
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            print("✅ (exists)")
                        else:
                            print(f"⚠️  {e}")
                
                # Create FTS infrastructure
                if fts_statements:
                    print(f"   🔍 Setting up full-text search ({fts_mode} mode)...")
                    for stmt in fts_statements:
                        if stmt.startswith("ALTER TABLE"):
                            print(f"      - Adding tsvector column...", end=" ")
                        elif "fts_expr" in stmt:
                            print(f"      - Creating expression index...", end=" ")
                        elif "ts_gin" in stmt:
                            print(f"      - Creating tsvector index...", end=" ")
                        else:
                            print(f"      - Executing FTS statement...", end=" ")
                        
                        try:
                            await ac.execute(text(stmt))
                            print("✅")
                        except Exception as e:
                            if "already exists" in str(e).lower():
                                print("✅ (exists)")
                            else:
                                print(f"⚠️  {e}")
            
            print("✅ Search infrastructure setup completed")
            return True
            
        except Exception as e:
            print(f"❌ Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"   🔄 Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                print("❌ Failed to set up search infrastructure after all retries")
                return False
    
    return False

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

async def reset_songs_table(session: AsyncSession):
    """Clear only the songs table; do not touch room-related tables."""
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
    """Upsert song into database"""
    try:
        res = await session.execute(select(Song).where(Song.id == song_id))
        existing = res.scalars().first()
        if existing:
            # Update existing song
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
            # Insert new song
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
    except Exception as e:
        print(f"         ❌ Database upsert error: {e}")
        raise

# ============================================================================
# SONG PROCESSING
# ============================================================================

async def process_one_song(
    session: AsyncSession, 
    song_id: str, 
    filename: str, 
    paths: Dict[str, str],
    regen_assets: bool = False
) -> Tuple[str, bool]:
    """Process a single song: generate PDF, images, and update database"""
    print(f"   🎵 Processing song {song_id}: {filename}")
    
    cho_path = os.path.join(paths['songs_dir'], filename)
    if not os.path.exists(cho_path):
        print(f"      ❌ ChordPro file not found: {cho_path}")
        return song_id, False

    # Parse metadata
    print(f"      📖 Parsing ChordPro metadata...", end=" ")
    default_title = os.path.splitext(filename)[0]
    md = parse_chordpro_metadata(cho_path, default_title)
    title = md.get("title") or default_title
    artist = md.get("artist")
    key_meta = md.get("key")
    tempo_meta = md.get("tempo")
    genre_meta = md.get("genre")
    language_meta = md.get("language")
    print(f"✅")
    print(f"         Title: {title}")
    print(f"         Artist: {artist}")
    if key_meta:
        print(f"         Key: {key_meta}")

    # Setup paths
    pdf_path = os.path.join(paths['songs_pdf_dir'], f"{song_id}.pdf")
    img_dir = os.path.join(paths['songs_img_dir'], song_id)

    # Check if PDF generation is needed
    need_pdf = regen_assets or not os.path.exists(pdf_path)
    if need_pdf:
        print(f"      📄 PDF generation needed")
    else:
        print(f"      📄 PDF exists, checking validity...", end=" ")

    # Read ChordPro content
    try:
        with open(cho_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        print(f"      📝 ChordPro content loaded ({len(content)} chars)")
    except Exception as e:
        print(f"      ❌ Failed to read ChordPro file: {e}")
        return song_id, False

    # Generate or validate PDF
    page_count: Optional[int] = None
    if need_pdf:
        try:
            page_count = await render_pdf_with_chordpro_or_fallback(cho_path, pdf_path, content)
        except Exception as e:
            print(f"      ❌ PDF generation failed: {e}")
            return song_id, False
    else:
        try:
            with fitz.open(pdf_path) as doc:
                page_count = doc.page_count
                print(f"✅ ({page_count} pages)")
        except Exception as e:
            print(f"❌ Invalid, regenerating...")
            try:
                page_count = await render_pdf_with_chordpro_or_fallback(cho_path, pdf_path, content)
            except Exception as e2:
                print(f"      ❌ PDF regeneration failed: {e2}")
                return song_id, False

    # Generate or validate WebP images
    need_images = regen_assets or not (os.path.isdir(img_dir) and 
                                      any(fn.endswith('.webp') for fn in os.listdir(img_dir)))
    if need_images:
        print(f"      🖼️  Image generation needed")
        try:
            await asyncio.to_thread(render_webp_from_pdf, pdf_path, img_dir)
        except Exception as e:
            print(f"      ❌ Image generation failed: {e}")
            return song_id, False
    else:
        try:
            existing_images = [f for f in os.listdir(img_dir) if f.endswith('.webp')]
            print(f"      🖼️  Images exist ({len(existing_images)} files) ✅")
        except Exception:
            print(f"      🖼️  Image directory issue, regenerating...")
            try:
                await asyncio.to_thread(render_webp_from_pdf, pdf_path, img_dir)
            except Exception as e:
                print(f"      ❌ Image generation failed: {e}")
                return song_id, False

    # Save to database
    print(f"      💾 Saving to database...", end=" ")
    try:
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
        print(f"✅")
        print(f"   ✅ Song {song_id} completed successfully")
        return song_id, True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return song_id, False

# ============================================================================
# MAIN PROCESSING FUNCTIONS
# ============================================================================

async def populate_database(paths: Dict[str, str], args) -> int:
    """Main database population function"""
    print_phase_header("🎵 DATABASE POPULATION")
    
    # Load metadata
    metadata = read_metadata(paths['metadata_path'])
    if not metadata:
        print("❌ No songs metadata found. Run GitHub sync first.")
        return 1
    
    # Normalize song IDs (remove leading zeros)
    from scripts.setup.shared_utils import normalize_metadata_ids
    original_count = len(metadata)
    metadata = normalize_metadata_ids(metadata)
    normalized_count = len(metadata)
    
    if original_count != normalized_count:
        print(f"⚠️  ID normalization changed count: {original_count} → {normalized_count}")
        # Save normalized metadata back
        if save_metadata(metadata, paths['metadata_path']):
            print(f"✅ Saved normalized metadata")
    
    print(f"📊 Found {len(metadata)} songs in metadata")
    
    # Filter songs if specific IDs requested
    if args.songs_only:
        requested_ids = set(args.songs_only.split(','))
        filtered_metadata = {k: v for k, v in metadata.items() if k in requested_ids}
        if not filtered_metadata:
            print(f"❌ None of the requested song IDs found: {args.songs_only}")
            return 1
        metadata = filtered_metadata
        print(f"🎯 Processing only {len(metadata)} requested songs")
    
    if args.regen_assets:
        print("🔄 Force regenerating all assets (PDF + WebP)")
    else:
        print("⚡ Using existing assets where available")

    # Database operations
    try:
        async with AsyncSessionLocal() as session:
            print(f"💾 Database session established")
            
            # Reset database if requested
            if args.reset_songs:
                print(f"🗑️  Clearing songs table...")
                await reset_songs_table(session)
                await session.commit()
                print(f"✅ Songs table cleared")
            
            # Process songs
            items = sorted(metadata.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else kv[0])
            sem = asyncio.Semaphore(max(1, args.concurrency))
            
            print_section_header(f"🚀 Processing {len(items)} songs")
            
            progress = ProgressTracker(len(items), "songs")
            
            async def worker(song_id: str, filename: str):
                async with sem:
                    try:
                        _, ok = await process_one_song(
                            session, song_id, filename, paths, 
                            regen_assets=args.regen_assets
                        )
                        progress.update(ok, f"Song {song_id}")
                        return ok
                    except Exception as e:
                        print(f"❌ Failed processing {song_id}:{filename} -> {e}")
                        progress.update(False, f"Song {song_id}")
                        return False

            tasks = [asyncio.create_task(worker(sid, fn)) for sid, fn in items]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Commit all changes
            print(f"\n💾 Committing to database...", end=" ")
            await session.commit()
            print(f"✅")
            
            # Summary
            total, success, failed = progress.summary()
            print_phase_header("📊 PROCESSING SUMMARY")
            print(f"✅ Successful: {success}")
            print(f"❌ Failed: {failed}")
            print(f"📊 Total: {total}")
            
            if success == total:
                print(f"\n🎉 ALL SONGS PROCESSED SUCCESSFULLY!")
                return 0
            elif success > 0:
                print(f"\n⚠️  PARTIAL SUCCESS - {success}/{total} songs processed")
                return 0
            else:
                print(f"\n💥 NO SONGS PROCESSED SUCCESSFULLY")
                return 1
                
    except Exception as e:
        print(f"💥 Database population failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

# ============================================================================
# MAIN FUNCTION
# ============================================================================

async def main(argv=None):
    """Main function for database population"""
    parser = argparse.ArgumentParser(description="Populate database with songs from local files")
    parser.add_argument("--reset-songs", action="store_true", help="Clear songs table before processing")
    parser.add_argument("--regen-assets", action="store_true", help="Force regenerate PDF and WebP assets")
    parser.add_argument("--concurrency", type=int, default=4, help="Concurrent processing tasks")
    parser.add_argument("--songs-only", type=str, help="Process only specific song IDs (comma-separated)")
    parser.add_argument("--check-missing", action="store_true", help="Find songs in DB but missing files")
    parser.add_argument("--verify-assets", action="store_true", help="Verify all assets exist and are valid")
    
    # Search infrastructure options
    parser.add_argument("--setup-search", action="store_true", help="Set up search infrastructure (pg_trgm, indexes)")
    parser.add_argument("--skip-search", action="store_true", help="Skip search infrastructure setup")
    parser.add_argument("--blocking-indexes", action="store_true", help="Use blocking index creation (faster but locks tables)")
    parser.add_argument("--fts-mode", choices=["none", "expr", "column"], help="Full-text search mode")
    args = parser.parse_args(argv)

    print("🎵 DATABASE POPULATION")
    print("=" * 60)
    
    # Setup environment
    if not setup_environment():
        print("⚠️  Continuing with system environment variables")
    
    # Validate environment
    env_ok, issues = validate_environment()
    if not env_ok:
        print("❌ Environment validation failed:")
        for issue in issues:
            print(f"   - {issue}")
        return 1
    
    # Get paths and ensure directories exist
    paths = get_data_paths()
    if not ensure_directories(paths):
        print("❌ Failed to create required directories")
        return 1
    
    print(f"📁 Data directory: {paths['data_dir']}")
    print(f"🎵 Songs directory: {paths['songs_dir']}")
    print(f"📄 PDFs directory: {paths['songs_pdf_dir']}")
    print(f"🖼️  Images directory: {paths['songs_img_dir']}")
    
    # Test database connection and create tables
    try:
        print(f"\n🔌 Testing database connection...")
        await create_db_and_tables_async()
        print(f"✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return 1
    
    # Set up search infrastructure (unless explicitly skipped)
    if not args.skip_search:
        # Override environment variables with command line args
        if args.setup_search:
            os.environ["ENABLE_SEARCH_INDEXES"] = "true"
        if args.blocking_indexes:
            os.environ["CONCURRENT_INDEXES"] = "false"
        if args.fts_mode:
            os.environ["FTS_MODE"] = args.fts_mode
        
        if not await setup_search_infrastructure():
            print("⚠️  Search infrastructure setup failed, but continuing...")
            print("   (Search functionality may be limited)")
    else:
        print("⏭️  Skipping search infrastructure setup (--skip-search)")
    
    # Run population
    try:
        return await populate_database(paths, args)
    except KeyboardInterrupt:
        print("\n⚠️  Population interrupted by user")
        return 130
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)