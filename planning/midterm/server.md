## What's already done:
- Set up complete FastAPI server w/ GCP
- Create/confirm endpoints for our features:
        - Songs
        - Rooms
- Setup API for converting ChordPro songs --> PNG/PDFs for Frontend to display
- CI Pipeline for smooth development
- Optimize code for speed
        - Integrate external resources as applicable (i.e PostgreSQL)
        

## What will be done
- CD aspect of CI/CD (external SSH into GCP)
- Full integration of database w/ PostgreSQL 
- Reduce to < 100ms per request
- Playlists:
        - Playlists feature allowing users to create playlists from the song db
        - User specific playlists can be played/queued by the host in the rooms
- Complete and thorough documentation for open-source release


## What is nice to have, but won't be done in this intern scope:
- MIDI Format (we are trying now):
        - Make a "band option" in the room so instead of displaying a picture of
        the chord sheet, it will display respective notes for the user to play live
        - Will involve scraping MIDI formatted songs alongside our current ChordPro
        database