#!/usr/bin/env python3
"""
Database connection test script for debugging PostgreSQL issues.
Run this before retrieve_songs.py to diagnose connection problems.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add server directory to path
SCRIPT_DIR = Path(__file__).parent
SERVER_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SERVER_DIR))

from dotenv import load_dotenv

# Load environment variables
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

# Test database connection
async def test_database_connection():
    try:
        from scripts.runtime.database import get_database_url, engine, create_db_and_tables_async
        from sqlalchemy import text
        
        # Get database URL
        db_url = get_database_url()
        print(f" Database URL: {db_url.split('@')[0]}@[REDACTED]")
        
        # Test basic connection
        print(" Testing database connection...")
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"Connected to PostgreSQL: {version}")
        
        # Test table creation
        print("Testing table creation...")
        await create_db_and_tables_async()
        print("Tables created/verified successfully")
        
        # Test basic query
        print("Testing basic query...")
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM songs"))
            count = result.scalar()
            print(f"Songs table accessible, contains {count} records")
        
        return True
        
    except Exception as e:
        print(f"Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_file_permissions():
    """Test file system permissions for song data directories"""
    try:
        from scripts.runtime.paths import get_database_dir
        
        data_dir = Path(get_database_dir())
        print(f"Data directory: {data_dir}")
        
        # Test directory creation and permissions
        test_dirs = [
            data_dir,
            data_dir / "songs",
            data_dir / "songs_pdf", 
            data_dir / "songs_img"
        ]
        
        for test_dir in test_dirs:
            test_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = test_dir / "test_write.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
                print(f"{test_dir} - writable")
            except Exception as e:
                print(f"{test_dir} - not writable: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"File permission test failed: {e}")
        return False

async def main():
    print(" Database Connection Diagnostic Tool")
    print("=" * 50)
    
    # Test environment variables
    print("\nEnvironment Variables:")
    required_vars = ["DATABASE_URL", "FIREBASE_JSON"]
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if var == "DATABASE_URL":
                # Mask password in URL
                masked = value.split('@')[0] + "@[REDACTED]" if '@' in value else "[REDACTED]"
                print(f"{var}: {masked}")
            else:
                print(f"{var}: [SET]")
        else:
            print(f"{var}: [NOT SET]")
    
    # Test file permissions
    print("\nFile System Tests:")
    fs_ok = await test_file_permissions()
    
    # Test database connection
    print("\nDatabase Tests:")
    db_ok = await test_database_connection()
    
    # Summary
    print("\nSummary:")
    if db_ok and fs_ok:
        print("All tests passed! retrieve_songs.py should work.")
        return 0
    else:
        print("Some tests failed. Fix the issues above before running retrieve_songs.py")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)