import streamlit as st
from scraper import song_scraper, chordpro_utils
import subprocess

st.title("ChordPro Scraper 🎶")

title = st.text_input("Song Title")
artist = st.text_input("Artist (optional)")
debug = st.checkbox("Debug mode")

if st.button("Scrape"):
    if not title.strip():
        st.error("❌ Please enter a song title.")
    else:
        st.write(f"Searching for '{title}'" + (f" by {artist}" if artist else "") + "...")
        try:
            raw_text = song_scraper.scrape_song_raw(title, artist)
            if not raw_text:
                st.error("❌ Could not retrieve any chords.")
            else:
                chordpro_text = chordpro_utils.process_raw_chords(raw_text)

                if not chordpro_utils.is_chordpro(chordpro_text):
                    st.warning("⚠️ Still not valid after cleanup, skipping save.")
                else:
                    save_path = song_scraper.save_to_file(title, artist, chordpro_text)
                    st.success(f"✅ Saved valid ChordPro to: {save_path}")

                    pdf_path = save_path.replace(".pro", ".pdf")
                    try:
                        subprocess.run(["chordpro", save_path, "--output", pdf_path], check=True)
                        st.info(f"📄 Also exported as PDF: {pdf_path}")
                    except FileNotFoundError:
                        st.warning("⚠️ chordpro binary not found. Install it and ensure it's on your PATH.")
                    except subprocess.CalledProcessError as e:
                        st.warning(f"⚠️ chordpro failed with exit code {e.returncode}")
        except Exception as e:
            st.error(f"❌ Error: {e}")