import os
import click
import asyncio
import subprocess


from scraper import song_scraper, chordpro_utils

@click.command()
@click.option('--title', '-t', prompt='Enter what you would wanna play', help='Song title to search for', required=True)
@click.option('--artist', '-a', prompt='Do you know the artist? (press Enter to skip)', default='', help='Artist name (optional)')
@click.option('--debug', is_flag=True, help='Enable debug output')
def main(title, artist, debug):
    title = title.strip()
    artist = artist.strip() or None

    print(f"Searching for '{title}'" + (f" by {artist}" if artist else "") + "...")

    # Step 1: Scrape raw text
    raw_text = song_scraper.scrape_song_raw(title, artist)
    if not raw_text:
        print("❌ Could not retrieve any chords.")
        return

    # Step 2: Validate + convert
    chordpro_text = chordpro_utils.process_raw_chords(raw_text)

    # Step 3: Only proceed if valid
    if not chordpro_utils.is_chordpro(chordpro_text):
        print("⚠️ Still not valid after cleanup, skipping save.")
        return

    # Step 4: Save as .pro
    save_path = song_scraper.save_to_file(title, artist, chordpro_text)
    print(f"\n✅ Saved valid ChordPro to: {save_path}")

    # Step 5: Render to PDF using chordpro binary directly
    pdf_path = save_path.replace(".pro", ".pdf")
    try:
        subprocess.run(
            ["chordpro", save_path, "--output", pdf_path],
            check=True
        )
        print(f"📄 Also exported as PDF: {pdf_path}")
    except FileNotFoundError:
        print("⚠️ chordpro binary not found. Install it and ensure it's on your PATH.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ chordpro failed with exit code {e.returncode}")



if __name__ == "__main__":
    main()