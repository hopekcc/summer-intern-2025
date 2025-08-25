import os
import json
import gzip
from io import BytesIO
from pathlib import Path
import sys
import asyncio
import warnings
from sqlalchemy.pool import StaticPool

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# NOTE: We purposely avoid importing server.main until after we set env/patch firebase
# Ensure correct import paths for both 'scripts.*' (under server/) and 'server.*' (package at project root)
_THIS_DIR = Path(__file__).resolve().parent
_SERVER_DIR = _THIS_DIR.parent
_PROJECT_ROOT = _SERVER_DIR.parent
for _p in (str(_SERVER_DIR), str(_PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Silence noisy deprecation warnings during tests
warnings.filterwarnings("ignore", category=DeprecationWarning)

@pytest.fixture(scope="session", autouse=True)
def prepared_env(tmp_path_factory):
    """Prepare environment so imports won't hit real services.
    - Provide a dummy Postgres DATABASE_URL to satisfy import-time checks.
    - Provide FIREBASE_JSON and stub firebase credential/init so import doesn't validate.
    - Patch the DB engine/session to use an in-memory sqlite+aiosqlite async engine.
    - Create tables up-front and seed songs from tests/testsongdata/songs_metadata.json.
    """
    # Env expected by scripts.runtime.database and server.main
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/test")
    os.environ.setdefault("FIREBASE_JSON", json.dumps({"fake": True}))
    os.environ.setdefault("DB_STARTUP_CHECK", "false")

    # Stub firebase credential creation and init BEFORE importing main
    import firebase_admin  # type: ignore
    from firebase_admin import credentials  # type: ignore

    # Return a benign object instead of validating service account fields
    credentials.Certificate = lambda *a, **kw: object()  # type: ignore
    # Pretend app already initialized and make initialize_app a no-op
    try:
        firebase_admin._apps = [object()]  # type: ignore[attr-defined]
    except Exception:
        pass
    firebase_admin.initialize_app = lambda *a, **kw: None  # type: ignore

    # Now import database module and patch its engine/session to sqlite for tests
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlmodel import SQLModel

    from scripts.runtime import database as db

    # Create a process-wide shared in-memory sqlite engine for async
    # StaticPool ensures a single connection is reused so the in-memory DB persists across sessions
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Patch engine and session factory
    db.engine = test_engine
    db.AsyncSessionLocal = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False)

    # Rebind the create tables function to use the patched engine
    async def _create_all():
        async with test_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
            await conn.commit()

    db.create_db_and_tables_async = _create_all  # type: ignore

    # Patch Postgres-specific add_participant to a SQLite-friendly implementation
    from sqlalchemy import select as _select
    async def _add_participant_sqlite(session, room_id: str, user_id: str):
        # No commit here; caller handles commit
        res = await session.execute(
            _select(db.RoomParticipant).where(
                db.RoomParticipant.room_id == room_id,
                db.RoomParticipant.user_id == user_id,
            )
        )
        if res.scalars().first() is None:
            session.add(db.RoomParticipant(room_id=room_id, user_id=user_id))

    db.add_participant = _add_participant_sqlite  # type: ignore

    # Create tables now so seeding can proceed safely
    asyncio.run(db.create_db_and_tables_async())

    # Read test song metadata if present to seed DB
    tests_dir = Path(__file__).parent
    metadata_path = tests_dir / "testsongdata" / "songs_metadata.json"
    song_entries = []
    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            # meta expected as { "1": "Title.ext", ... }
            for sid, fname in meta.items():
                title = Path(fname).stem
                song_entries.append({
                    "id": str(sid),
                    "title": title or f"Song {sid}",
                    "artist": "Test Artist",
                    "page_count": 1,
                    "filename": f"{sid}.pdf",
                })
        except Exception:
            # Fallback to a single default entry if malformed
            song_entries = [{"id": "003", "title": "Test Song 003", "artist": "Test Artist", "page_count": 1, "filename": "003.pdf"}]
    else:
        song_entries = [{"id": "003", "title": "Test Song 003", "artist": "Test Artist", "page_count": 1, "filename": "003.pdf"}]

    # Seed songs
    async def _seed_songs():
        async with db.AsyncSessionLocal() as session:
            for e in song_entries:
                song = db.Song(id=e["id"], title=e["title"], artist=e["artist"], page_count=e["page_count"], filename=e["filename"])
                session.add(song)
            await session.commit()

    asyncio.run(_seed_songs())

    # Make song entries available to later fixtures via env variable
    os.environ["TEST_SONG_ENTRIES_JSON"] = json.dumps(song_entries)

    # Return a base assets directory for sessions if needed
    return tmp_path_factory.mktemp("assets_base")


@pytest.fixture()
def client(prepared_env, tmp_path, monkeypatch):
    """Provide a TestClient with dependency overrides for filesystem paths and auth.
    Creates synthetic assets (PDF, WEBP) and a songs_list.json.gz pointing to ID 003.
    """
    # Build expected directory layout
    database_dir = tmp_path
    songs_pdf_dir = database_dir / "songs_pdf"
    songs_img_root = database_dir / "songs_img"
    songs_pdf_dir.mkdir(parents=True, exist_ok=True)
    songs_img_root.mkdir(parents=True, exist_ok=True)

    # Read seeded entries from env and create matching assets and gz list
    entries = json.loads(os.environ.get("TEST_SONG_ENTRIES_JSON", "[]") or "[]")
    songs_list_gz = database_dir / "songs_list.json.gz"
    for e in entries:
        sid = e["id"]
        # PDF
        pdf_path = songs_pdf_dir / f"{sid}.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.drawString(100, 750, f"Test PDF for {sid}")
        c.showPage()
        c.save()
        # Image
        song_img_dir = songs_img_root / sid
        song_img_dir.mkdir(parents=True, exist_ok=True)
        img_path = song_img_dir / "page_1.webp"
        img = Image.new("RGB", (100, 100), color=(200, 100, 50))
        img.save(str(img_path), format="WEBP")
    # Gz list mirrors the DB seed
    with gzip.open(str(songs_list_gz), "wb") as f:
        f.write(json.dumps([{k: v for k, v in e.items() if k in ("id", "title", "artist", "page_count")} for e in entries]).encode("utf-8"))

    # Import after env prepared
    import server.main as main

    # Disable starting the websocket server during app startup
    async def _ws_noop(*args, **kwargs):
        return None
    monkeypatch.setattr(main, "start_websocket_server", _ws_noop)

    # Ensure app.startup sets state directories to our temp database_dir
    # Note: main imports get_database_dir at module import, so patch main.get_database_dir
    from scripts.runtime import paths as paths_mod
    monkeypatch.setattr(main, "get_database_dir", lambda: str(database_dir))

    # Dependency overrides: auth -> dummy user
    from scripts.runtime.auth_middleware import get_current_user
    main.app.dependency_overrides[get_current_user] = lambda: {"uid": "test-user", "email": "test@example.com"}

    # Dependency overrides: filesystem path providers
    from scripts.runtime.paths import get_songs_pdf_dir, get_songs_img_dir, get_songs_list_gzip_path
    main.app.dependency_overrides[get_songs_pdf_dir] = lambda: str(songs_pdf_dir)
    main.app.dependency_overrides[get_songs_img_dir] = lambda: str(songs_img_root)
    main.app.dependency_overrides[get_songs_list_gzip_path] = lambda: str(songs_list_gz)

    # Yield a live TestClient (manages FastAPI lifespan)
    with TestClient(main.app) as test_client:
        yield test_client
