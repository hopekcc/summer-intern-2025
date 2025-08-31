#!/usr/bin/env python3
"""
Songs Database Pipeline Wrapper
Main orchestrator for the complete song database setup process.
Coordinates GitHub sync, database population, and diagnostics.
"""

import os
import sys
import asyncio
import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple, List

# Add server directory to path
SCRIPT_DIR = Path(__file__).parent
SERVER_DIR = SCRIPT_DIR.parent.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from scripts.setup.shared_utils import (
    setup_environment, validate_environment, get_data_paths,
    print_phase_header, print_section_header
)

# ============================================================================
# PREREQUISITE CHECKS
# ============================================================================

def check_prerequisites() -> Tuple[bool, List[str]]:
    """Check if all prerequisites are met"""
    issues = []
    
    # Check Python version
    if sys.version_info < (3, 8):
        issues.append(f"Python 3.8+ required, got {sys.version}")
    
    # Check required packages
    required_packages = [
        ("sqlalchemy", "SQLAlchemy"),
        ("asyncpg", "asyncpg"),
        ("httpx", "HTTPX"),
        ("pillow", "Pillow"),
        ("fitz", "PyMuPDF"),
        ("reportlab", "ReportLab"),
        ("dotenv", "python-dotenv")
    ]
    
    for import_name, display_name in required_packages:
        try:
            __import__(import_name.replace("-", "_"))
        except ImportError:
            issues.append(f"Missing required package: {display_name}")
    
    return len(issues) == 0, issues

def run_diagnostics() -> bool:
    """Run database connection diagnostics"""
    print_section_header("🧪 Running diagnostics")
    
    try:
        test_script = SCRIPT_DIR / "test_db_connection.py"
        if not test_script.exists():
            print("⚠️  Diagnostic script not found, skipping...")
            return True
        
        result = subprocess.run(
            [sys.executable, str(test_script)], 
            capture_output=True, 
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✅ All diagnostic tests passed")
            return True
        else:
            print("❌ Diagnostic tests failed:")
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Diagnostic tests timed out")
        return False
    except Exception as e:
        print(f"💥 Error running diagnostics: {e}")
        return False

# ============================================================================
# PIPELINE PHASES
# ============================================================================

async def run_github_sync(args) -> bool:
    """Run GitHub synchronization phase"""
    print_phase_header("🌐 GITHUB SYNC PHASE")
    
    try:
        # Import and run the sync function
        from scripts.setup.retrieve_songs_new import main as sync_main
        
        # Build arguments for sync script
        sync_args = []
        if args.dry_run:
            sync_args.append("--dry-run")
        if args.force_download:
            sync_args.append("--force-download")
        if args.no_cleanup:
            sync_args.append("--no-cleanup")
        
        result = await sync_main(sync_args)
        
        if result == 0:
            print("✅ GitHub sync completed successfully")
            return True
        else:
            print(f"❌ GitHub sync failed with exit code: {result}")
            return False
            
    except Exception as e:
        print(f"💥 GitHub sync error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_database_population(args) -> bool:
    """Run database population phase"""
    print_phase_header("💾 DATABASE POPULATION PHASE")
    
    try:
        # Import and run the population function
        from scripts.setup.populate_db import main as populate_main
        
        # Build arguments for population script
        pop_args = []
        if args.reset_songs:
            pop_args.append("--reset-songs")
        if args.regen_assets:
            pop_args.append("--regen-assets")
        if args.concurrency:
            pop_args.extend(["--concurrency", str(args.concurrency)])
        if args.songs_only:
            pop_args.extend(["--songs-only", args.songs_only])
        if args.check_missing:
            pop_args.append("--check-missing")
        if args.verify_assets:
            pop_args.append("--verify-assets")
        if args.setup_search:
            pop_args.append("--setup-search")
        if args.skip_search:
            pop_args.append("--skip-search")
        if args.blocking_indexes:
            pop_args.append("--blocking-indexes")
        if args.fts_mode:
            pop_args.extend(["--fts-mode", args.fts_mode])
        
        result = await populate_main(pop_args)
        
        if result == 0:
            print("✅ Database population completed successfully")
            return True
        else:
            print(f"❌ Database population failed with exit code: {result}")
            return False
            
    except Exception as e:
        print(f"💥 Database population error: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# MAIN PIPELINE ORCHESTRATOR
# ============================================================================

async def run_full_pipeline(args) -> int:
    """Run the complete pipeline"""
    start_time = time.time()
    
    print("🎵 SONGS DATABASE PIPELINE")
    print("=" * 80)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Phase 1: Prerequisites
    print_phase_header("🔍 PREREQUISITE CHECKS")
    
    prereq_ok, issues = check_prerequisites()
    if not prereq_ok:
        print("❌ Prerequisites check failed:")
        for issue in issues:
            print(f"   - {issue}")
        return 1
    print("✅ Prerequisites check passed")
    
    # Phase 2: Environment setup
    print_section_header("📋 Environment setup")
    if not setup_environment():
        print("⚠️  Continuing with system environment variables")
    
    env_ok, env_issues = validate_environment()
    if not env_ok:
        print("❌ Environment validation failed:")
        for issue in env_issues:
            print(f"   - {issue}")
        return 1
    print("✅ Environment validation passed")
    
    # Phase 3: Diagnostics (unless skipped)
    if not args.skip_diagnostics:
        if not run_diagnostics():
            if not args.ignore_diagnostic_failures:
                print("❌ Diagnostic tests failed. Use --ignore-diagnostic-failures to continue anyway.")
                return 1
            else:
                print("⚠️  Diagnostic tests failed but continuing due to --ignore-diagnostic-failures")
    
    # Phase 4: GitHub Sync (unless populate-only)
    sync_success = True
    if not args.populate_only:
        sync_success = await run_github_sync(args)
        if not sync_success and not args.ignore_sync_failures:
            print("❌ GitHub sync failed. Use --ignore-sync-failures to continue anyway.")
            return 1
    
    # Phase 5: Database Population (unless sync-only)
    populate_success = True
    if not args.sync_only:
        populate_success = await run_database_population(args)
        if not populate_success:
            return 1
    
    # Final summary
    end_time = time.time()
    duration = end_time - start_time
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    
    print("\n" + "=" * 80)
    print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Total duration: {minutes}m {seconds}s")
    
    if sync_success and populate_success:
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        
        # Show final status
        paths = get_data_paths()
        from scripts.setup.shared_utils import read_metadata
        metadata = read_metadata(paths['metadata_path'])
        
        print_phase_header("📊 FINAL STATUS")
        print(f"📊 Total songs: {len(metadata)}")
        print(f"📁 Songs directory: {paths['songs_dir']}")
        print(f"📄 PDFs directory: {paths['songs_pdf_dir']}")
        print(f"🖼️  Images directory: {paths['songs_img_dir']}")
        print(f"💾 Database: Ready for use")
        
        return 0
    else:
        print("⚠️  PIPELINE COMPLETED WITH ISSUES")
        return 1

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Songs Database Pipeline - Complete setup orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline (default)
  python songs_db_pipeline_wrapper.py
  
  # Only sync from GitHub
  python songs_db_pipeline_wrapper.py --sync-only
  
  # Only populate database
  python songs_db_pipeline_wrapper.py --populate-only
  
  # Full pipeline with asset regeneration
  python songs_db_pipeline_wrapper.py --regen-assets
  
  # Process specific songs only
  python songs_db_pipeline_wrapper.py --populate-only --songs-only 001,002,003
        """
    )
    
    # Pipeline control
    parser.add_argument("--sync-only", action="store_true", 
                       help="Only run GitHub sync phase")
    parser.add_argument("--populate-only", action="store_true", 
                       help="Only run database population phase")
    parser.add_argument("--skip-diagnostics", action="store_true", 
                       help="Skip database connection diagnostics")
    parser.add_argument("--ignore-diagnostic-failures", action="store_true", 
                       help="Continue even if diagnostics fail")
    parser.add_argument("--ignore-sync-failures", action="store_true", 
                       help="Continue to population even if sync fails")
    
    # GitHub sync options
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be done without making changes")
    parser.add_argument("--force-download", action="store_true", 
                       help="Re-download all files even if they exist")
    parser.add_argument("--no-cleanup", action="store_true", 
                       help="Skip cleanup of orphaned files")
    
    # Database population options
    parser.add_argument("--reset-songs", action="store_true", 
                       help="Clear songs table before processing")
    parser.add_argument("--regen-assets", action="store_true", 
                       help="Force regenerate PDF and WebP assets")
    parser.add_argument("--concurrency", type=int, default=4, 
                       help="Concurrent processing tasks")
    parser.add_argument("--songs-only", type=str, 
                       help="Process only specific song IDs (comma-separated)")
    parser.add_argument("--check-missing", action="store_true", 
                       help="Find songs in DB but missing files")
    parser.add_argument("--verify-assets", action="store_true", 
                       help="Verify all assets exist and are valid")
    
    # Search infrastructure options
    parser.add_argument("--setup-search", action="store_true", 
                       help="Set up search infrastructure (pg_trgm, indexes)")
    parser.add_argument("--skip-search", action="store_true", 
                       help="Skip search infrastructure setup")
    parser.add_argument("--blocking-indexes", action="store_true", 
                       help="Use blocking index creation (faster but locks tables)")
    parser.add_argument("--fts-mode", choices=["none", "expr", "column"], 
                       help="Full-text search mode")
    
    args = parser.parse_args()
    
    # Validate argument combinations
    if args.sync_only and args.populate_only:
        print("❌ Cannot specify both --sync-only and --populate-only")
        return 1
    
    try:
        return asyncio.run(run_full_pipeline(args))
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
        return 130
    except Exception as e:
        print(f"\n💥 Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())