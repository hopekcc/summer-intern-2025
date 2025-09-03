import os
import json

import pytest

# The `client` fixture is provided by tests/conftest.py


def _get_first_entry():
    entries = json.loads(os.environ.get("TEST_SONG_ENTRIES_JSON", "[]") or "[]")
    assert entries, "TEST_SONG_ENTRIES_JSON not populated by conftest"
    return entries[0]


def test_engine_is_sqlite_not_postgres():
    # Ensure tests are not using Postgres
    from scripts.runtime.database import engine
    assert engine.dialect.name == "sqlite"


def test_song_metadata_structure(client):
    e = _get_first_entry()
    sid = e["id"]
    r = client.get(f"/songs/{sid}")
    assert r.status_code == 200
    data = r.json()
    # Required fields
    for key in ("id", "title", "artist", "page_count", "pdf_url", "image_url", "total_pages"):
        assert key in data, f"missing {key}"
    assert data["id"] == sid
    assert isinstance(data["title"], str)
    assert isinstance(data["artist"], (str, type(None)))
    assert isinstance(data["page_count"], int)
    # pdf_url present and not null when asset exists
    assert data["pdf_url"] == f"/songs/{sid}/pdf"
    assert data["image_url"] == f"/songs/{sid}/image"
    assert data["total_pages"] == e["page_count"]


def test_song_pdf_serving(client):
    sid = _get_first_entry()["id"]
    r = client.get(f"/songs/{sid}/pdf")
    assert r.status_code == 200
    assert r.headers.get("content-type") == "application/pdf"
    assert "ETag" in r.headers
    assert "Cache-Control" in r.headers


def test_song_image_cover(client):
    sid = _get_first_entry()["id"]
    r = client.get(f"/songs/{sid}/image")
    assert r.status_code == 200
    assert r.headers.get("content-type") == "image/webp"
    assert "ETag" in r.headers


def test_song_page_image_bounds(client):
    sid = _get_first_entry()["id"]
    ok = client.get(f"/songs/{sid}/page/1")
    assert ok.status_code == 200
    bad = client.get(f"/songs/{sid}/page/2")
    assert bad.status_code == 404


def test_songs_list_json_gzip(client):
    r = client.get("/songs/list")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # Ensure at least the seeded entry is present and keys match expected
    e = _get_first_entry()
    found = next((x for x in data if x.get("id") == e["id"]), None)
    assert found is not None
    for key in ("id", "title", "artist", "page_count"):
        assert key in found

