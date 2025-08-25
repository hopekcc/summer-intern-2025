import json
from contextlib import contextmanager


@contextmanager
def as_user(client, uid: str, email: str = None):
    """Temporarily override auth dependency to act as a specific user."""
    app = client.app
    # Import here (after fixtures prepare env and app) to avoid import-time DB checks
    from scripts.runtime.auth_middleware import get_current_user
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: {
        "uid": uid,
        "email": email or f"{uid}@example.com",
    }
    try:
        yield
    finally:
        if prev is None:
            del app.dependency_overrides[get_current_user]
        else:
            app.dependency_overrides[get_current_user] = prev


def test_rooms_end_to_end_flow(client):
    # Host is the default user from conftest: uid = "test-user"
    # 1) Create room
    r = client.post("/rooms/")
    assert r.status_code == 200, r.text
    room_id = r.json()["room_id"]
    assert isinstance(room_id, str) and len(room_id) > 0

    # 1b) Host joins as participant so that a later leave will close the room
    r = client.post(f"/rooms/{room_id}/join")
    assert r.status_code == 200, r.text

    # 2) Join as a different participant
    with as_user(client, "guest-1"):
        r = client.post(f"/rooms/{room_id}/join")
        assert r.status_code == 200, r.text
        assert "joined" in r.json()["message"].lower()

    # 3) Room details should list the participant
    r = client.get(f"/rooms/{room_id}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["room_id"] == room_id
    assert isinstance(data["participants"], list)
    assert "guest-1" in data["participants"]
    assert "test-user" in data["participants"]

    # 4) Select a song as host (pick the first available from /songs/)
    r = client.get("/songs/")
    assert r.status_code == 200, r.text
    songs = r.json()
    assert isinstance(songs, list) and len(songs) >= 1
    song_id = songs[0]["id"]
    r = client.post(f"/rooms/{room_id}/song", json={"song_id": song_id})
    assert r.status_code == 200, r.text
    sel = r.json()
    assert sel["song_id"] == song_id
    assert sel["current_page"] == 1

    # 5) Update to a valid page (1 is valid since page_count=1)
    r = client.post(f"/rooms/{room_id}/page", json={"page": 1})
    assert r.status_code == 200, r.text

    # 6) Update to an out-of-range page (2) -> expect 400
    r = client.post(f"/rooms/{room_id}/page", json={"page": 2})
    assert r.status_code == 400
    err = r.json()
    # Structure: {"detail": {"code": "PAGE_OUT_OF_RANGE", ...}}
    assert "detail" in err and isinstance(err["detail"], dict)
    assert err["detail"].get("code") == "PAGE_OUT_OF_RANGE"

    # 7) Sync state reflects selected song and page
    r = client.get(f"/rooms/{room_id}/sync")
    assert r.status_code == 200, r.text
    sync = r.json()
    assert sync["room_id"] == room_id
    assert sync["current_song"] == song_id
    assert sync["current_page"] == 1
    assert isinstance(sync.get("participants"), list)

    # 8) PDF endpoint should serve the file
    r = client.get(f"/rooms/{room_id}/pdf")
    assert r.status_code == 200, r.text
    assert r.headers.get("Content-Type", "").startswith("application/pdf")
    assert "ETag" in r.headers

    # 9) Image endpoint returns 200 then 304 on conditional GET
    r = client.get(f"/rooms/{room_id}/image")
    assert r.status_code == 200, r.text
    etag = r.headers.get("ETag")
    assert etag

    r2 = client.get(f"/rooms/{room_id}/image", headers={"If-None-Match": etag})
    assert r2.status_code == 304

    # 10) Guest leaves
    with as_user(client, "guest-1"):
        r = client.post(f"/rooms/{room_id}/leave")
        assert r.status_code == 200

    # 11) Host leaves -> room closed
    r = client.post(f"/rooms/{room_id}/leave")
    assert r.status_code == 200

    # 12) Room details should now be 404
    r = client.get(f"/rooms/{room_id}")
    assert r.status_code == 404
