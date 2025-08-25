# summer-intern-2025
HopeKCC Summer intern project - Tech meets Music

## Quick Links

- Setup Guide: `docs/SETUP.md`
- Server Spec (OnSleekApiQT): `server/aakash/server.md`
- Sleek GUI (desktop client): `docs/SLEEKGUI.md`
- Performance Test Suite: `server/aakash/performance_test.py`

## Getting Started

1) Follow `docs/SETUP.md` to configure `server/.env`, install deps, and run FastAPI locally.
2) Optional: generate and serve a gzipped songs catalog manifest for faster `/songs/list`.
3) Use `docs/SLEEKGUI.md` to run the consolidated Sleek GUI (`server/aakash/sleekgui.py`).
4) Validate metadata-only WebSocket events and strong ETag image caching per `server/aakash/server.md`.
5) Benchmark with `server/aakash/performance_test.py` using `--baseline` or `--optimized` (cleanup is opt-in via `--cleanup`).
