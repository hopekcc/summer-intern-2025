# HopeKCC Summer 2025 Internship Project

Welcome to the HopeKCC 2025 Summer Internship repository! This is the collaborative workspace for our intern teams—server, website, mobile, and shared utilities—working together to bring the **ChordPro music sync platform** to life.

---

## Project Overview

This project aims to create a synchronized, multi-device sheet music display system using **ChordPro**. The platform includes:

- **Web Admin UI** for uploading/editing songs and building setlists  
- **FastAPI Backend** for managing files, rendering ChordPro to image/PDF, and handling auth  
- **Mobile Apps** (host + clients) for synchronized display control  
- **Shared Infrastructure** for testing, deployment, and reusable code modules  

All code is maintained here collaboratively across tracks. See [`song-db-chordpro`](https://github.com/hopekcc/song-db-chordpro) for the ChordPro database repo used by this project.

---

## Folder Structure
.
├── LICENSE # Open source license
├── README.md # This file
├── docs/ # Setup guides, API specs, and weekly expectations
├── mobile/ # Native Android client apps
├── planning/ # Weekly check-ins, goals, retrospectives
├── server/ # FastAPI backend, ChordPro rendering, auth
├── shared/ # Reusable modules (utils, schemas, etc.)
└── website/ # Admin UI using Jinja2 + FastAPI routes


---

## Branch Naming Convention

To maintain consistency across our Git workflow, **please use the following naming format** when creating new branches:
<yourname>/<feature_name_with_underscores>

**Examples:**
sabrina/fetch_chordpro_metadata
jonathan/mobile_ui_sync
ryan/setup_fastapi_server


---

## Git SSH Setup for Google Cloud (First-Time Only)

To set up your SSH key and push/pull securely via Git:


## Song Database repo
https://github.com/hopekcc/song-db-chordpro

# Contributions
All interns are expected to:

- Submit regular code updates and documentation
- Write meaningful commit messages
- Create clean PRs and review at least 2 others per week
- Update weekly logs and song contributions under planning/ and songs/ (as applicable)


