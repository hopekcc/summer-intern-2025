"""
Song Scraper Module
Web scraping utility for fetching chord charts from multiple online sources.
Supports Ultimate Guitar, Chordie, and other chord sites with ChordPro conversion.
"""

import os
import re
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ============================================================================
# CONFIGURATION AND SETUP
# ============================================================================

# Configure logging for debug mode
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Default level, override to DEBUG for verbose output

# Environment-configurable settings
SONGS_DIR = os.getenv("SONGS_DIR", "songs")
COMMIT_TO_GIT = os.getenv("COMMIT_TO_GIT", "False").lower() in ("true", "1", "yes")

# Ensure the songs directory exists
os.makedirs(SONGS_DIR, exist_ok=True)

# ============================================================================
# FILE MANAGEMENT FUNCTIONS
# ============================================================================

def save_to_file(title: str, artist: str, content: str) -> str:
    """
    Save ChordPro content to the songs directory with a safe filename.
    
    Args:
        title: Song title
        artist: Artist name (optional)
        content: ChordPro formatted content
        
    Returns:
        str: Absolute file path of saved file
    """
    filename = f"{title}{' - ' + artist if artist else ''}.pro"
    safe_name = filename.replace(os.sep, "_").replace("..", "_")
    save_path = os.path.join(SONGS_DIR, safe_name)
    
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    
    logger.info(f"Saved chords to {save_path}")
    return os.path.abspath(save_path)

def find_local_song(title: str, artist: str = None) -> str:
    """
    Check the local songs directory for an existing chord file.
    
    Args:
        title: Song title to search for
        artist: Optional artist name for more specific matching
        
    Returns:
        str: File path if found, None otherwise
        
    Note:
        Searches for files with extensions: .pro, .cho, .chopro
    """
    title_norm = title.lower()
    artist_norm = artist.lower() if artist else None
    found_file = None
    
    for filename in os.listdir(SONGS_DIR):
        if not filename.lower().endswith((".pro", ".cho", ".chopro")):
            continue
            
        name = filename.lower()
        if title_norm in name and (artist_norm is None or artist_norm in name):
            found_file = os.path.join(SONGS_DIR, filename)
            break
    
    if found_file:
        logger.info(f"Found local file for '{title}'{' by ' + artist if artist else ''}: {found_file}")
    else:
        logger.info(f"No local file found for '{title}'{' by ' + artist if artist else ''}")
    
    return found_file

# ============================================================================
# WEB DRIVER MANAGEMENT
# ============================================================================

def init_selenium_driver() -> webdriver.Chrome:
    """
    Initialize a headless Chrome WebDriver using webdriver-manager.
    
    Returns:
        webdriver.Chrome: Configured Chrome driver instance
        
    Note:
        Driver runs in headless mode with security and performance optimizations
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode (no GUI)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Additional options can be added for stealth or performance as needed
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# ============================================================================
# WEB SCRAPING FUNCTIONS
# ============================================================================

def scrape_from_ultimate_guitar(title: str, artist: str = None) -> str:
    """
    Attempt to find and scrape chords from Ultimate Guitar.
    
    Args:
        title: Song title to search for
        artist: Optional artist name for more specific search
        
    Returns:
        str: Raw chord/lyric text if found, None otherwise
        
    Note:
        Uses Selenium to navigate search results and extract chord content
    """
    query = title
    if artist:
        query += f" {artist}"
    logger.info(f"Searching Ultimate Guitar for '{query}'...")
    driver = init_selenium_driver()
    try:
        # Use UG search page to find the song chords page
        search_url = f"https://www.ultimate-guitar.com/search.php?search_type=title&value={query}"
        driver.get(search_url)
        time.sleep(2)  # wait for results to load (can be replaced with explicit waits)
        # Find the first search result link that is a "Chords" type tab
        # Ultimate Guitar uses links containing "-chords-" for chord sheets:contentReference[oaicite:1]{index=1}.
        result_elems = driver.find_elements("xpath", "//a[contains(@href, '-chords-')]")
        song_url = None
        for elem in result_elems:
            href = elem.get_attribute("href")
            if href and "/tab/" in href and "chords" in href.lower():
                song_url = href
                break
        if not song_url:
            logger.info("No Ultimate Guitar chords result found.")
            return None
        logger.info(f"Found Ultimate Guitar URL: {song_url}")
        driver.get(song_url)
        # Wait for the chord/lyric content to load (UG content is dynamic):contentReference[oaicite:2]{index=2}
        # We'll wait until chord spans are present in the DOM.
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(@class, '_3bHP1')]"))
            )
        except Exception as e:
            logger.warning("Timed out waiting for Ultimate Guitar content to load.")
        page_html = driver.execute_script("return document.body.innerHTML;")
    finally:
        driver.quit()
    # Parse the HTML to extract chords and lyrics text
    raw_text = ""
    try:
        # Replace chord span elements with [chord] and get text:contentReference[oaicite:3]{index=3}
        import bs4
        soup = bs4.BeautifulSoup(page_html, "html.parser")
        # Each chord is in a span with classes like _3bHP1 _3ffP6; replace them with [ChordName]
        for chord_span in soup.find_all("span", {"class": "_3bHP1 _3ffP6"}):
            chord = chord_span.get_text(strip=True)
            chord_span.replace_with(f"[{chord}]")
        # Now get the text of the relevant content container
        # Typically chords and lyrics are under a <pre> or a <div> container with class 'js-tab-content'
        content_div = soup.find("pre") or soup.find("div", {"class": "js-tab-content"})
        raw_text = content_div.get_text(separator="\n") if content_div else soup.get_text(separator="\n")
    except Exception as e:
        logger.error(f"Error parsing Ultimate Guitar HTML: {e}")
    if raw_text:
        logger.info("Scraped song text from Ultimate Guitar.")
    return raw_text or None

def scrape_from_chordie(title: str, artist: str = None) -> str:
    """
    Attempt to search Chordie for the song and retrieve ChordPro-formatted chords and lyrics.
    
    Args:
        title: Song title to search for
        artist: Optional artist name for more specific search
        
    Returns:
        str: ChordPro formatted text if found, None otherwise
        
    Note:
        Attempts to switch to ChordPro view if available on the site
    """
    query = title
    if artist:
        query += f" {artist}"
    logger.info(f"Searching Chordie for '{query}'...")
    driver = init_selenium_driver()
    chordpro_text = None
    try:
        driver.get("https://www.chordie.com/")
        # Chordie has a search interface; enter the query and submit
        # (Assuming there's an input field with name 'q' or id 'term')
        search_box = None
        try:
            search_box = driver.find_element("name", "q")
        except Exception:
            try:
                search_box = driver.find_element("id", "q")
            except Exception:
                search_box = None
        if not search_box:
            logger.error("Chordie search input not found on page.")
            return None
        search_box.send_keys(query)
        search_box.submit()
        time.sleep(2)
        # Click the first search result link (if any results are found)
        result_links = driver.find_elements("xpath", "//ul[@class='results']//a")
        if not result_links:
            logger.info("No Chordie search results found.")
            return None
        song_link = result_links[0]
        song_title = song_link.text
        logger.info(f"Chordie result found: {song_title}. Fetching chords page...")
        song_link.click()
        time.sleep(2)
        # On the song page, switch to ChordPro view if available
        # (Chordie allows viewing in ChordPro format via a "View -> ChordPro" option:contentReference[oaicite:4]{index=4}.)
        try:
            # If there's a "View" dropdown or button:
            view_btn = driver.find_element("link text", "View")
            view_btn.click()
            chordpro_option = driver.find_element("link text", "ChordPro")
            chordpro_option.click()
            time.sleep(1)
        except Exception as e:
            # If direct click fails, perhaps already in chord view or another method needed
            logger.debug(f"ChordPro view switch not clickable: {e}")
        # Now get the page text which should be in ChordPro format
        page_text = driver.find_element("tag name", "body").text
        chordpro_text = page_text.strip()
    finally:
        driver.quit()
    if chordpro_text:
        logger.info("Retrieved ChordPro text from Chordie.")
    return chordpro_text or None

def scrape_from_guitarsongdownload(title: str, artist: str = None) -> str:
    """
    Attempt to find chords from GuitarSongDownload (if applicable).
    This might involve searching that site or using an API if available.
    Currently a placeholder – returns None if not implemented.
    """
    logger.info(f"Searching GuitarSongDownload for '{title} {artist or ''}'...")
    # NOTE: Implementation for this source depends on its available interface.
    # This could involve an HTTP request to a known URL pattern or a web scrape similar to above.
    # Placeholder: not implemented, so return None.
    return None

# ============================================================================
# CHORDPRO CONVERSION UTILITIES
# ============================================================================

def convert_to_chordpro(chord_text: str) -> str:
    """
    Convert lyrics with chords in 'chords above lyrics' format into inline ChordPro format.
    
    Args:
        chord_text: Raw text with chords above lyrics
        
    Returns:
        str: ChordPro formatted text with inline chord notation
        
    Note:
        Processes chord lines followed by lyric lines and merges them appropriately
    """
    lines = chord_text.splitlines()
    converted_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _is_chord_line(line) and i + 1 < len(lines) and not _is_chord_line(lines[i+1]):
            chord_line = line
            lyric_line = lines[i+1]
            merged = _merge_chord_line(chord_line, lyric_line)
            converted_lines.append(merged)
            i += 2  # skip the lyric line as well, since we've processed it
        else:
            # If it's not a chord line (or no following lyric), just append the line as is
            converted_lines.append(line)
            i += 1
    result = "\n".join(converted_lines)
    return result

def _is_chord_line(line: str) -> bool:
    """Heuristics to determine if a line consists of chords (with possible spacing) rather than lyrics."""
    # A simple check: line should contain mostly valid chord symbols and spaces, and very few lowercase letters that aren't in chord suffixes.
    tokens = line.strip().split()
    if not tokens:
        return False
    chord_pattern = re.compile(r'^[A-G][#b]?(?:m|maj|min|dim|aug|sus|add)?\d*(?:/[A-G][#b]?)?$')
    valid_tokens = 0
    for token in tokens:
        if chord_pattern.match(token):
            valid_tokens += 1
        else:
            return False
    # If all tokens match chord pattern and at least one token is present, treat as chord line
    return valid_tokens == len(tokens) and valid_tokens > 0

def _merge_chord_line(chord_line: str, lyric_line: str) -> str:
    """
    Merge a chords line with the following lyrics line into a single ChordPro-formatted line.
    Chords from chord_line will be inserted at the appropriate positions (above the corresponding lyric characters) in lyric_line.
    """
    # Convert to list of characters for easy insertion
    lyric_chars = list(lyric_line)
    # We will insert chords from rightmost to leftmost to avoid index shifting issues
    inserts = []
    # Use a regex to find chords and their positions in the chord_line by scanning through characters
    pos = 0
    # Iterate through chord_line characters to capture chord text and its index
    while pos < len(chord_line):
        if chord_line[pos].strip() == "":  # whitespace, skip
            pos += 1
            continue
        # If we find a non-space, that should be start of a chord token
        start = pos
        # collect full chord token (letters, #, /, etc until a space or end)
        while pos < len(chord_line) and chord_line[pos] != " ":
            pos += 1
        chord_token = chord_line[start:pos]
        # Determine insertion index in lyric_line: use the start index of the chord token
        insert_idx = start
        if insert_idx > len(lyric_chars):
            insert_idx = len(lyric_chars)
        inserts.append((insert_idx, chord_token))
    # Insert chords in reverse order (so indices remain correct for earlier inserts)
    for insert_idx, chord_token in sorted(inserts, key=lambda x: x[0], reverse=True):
        chord_markup = f"[{chord_token}]"
        # Insert the chord markup at the determined position in the lyric text
        lyric_chars[insert_idx:insert_idx] = list(chord_markup)
    merged_line = "".join(lyric_chars)
    return merged_line

def validate_chordpro_format(text: str) -> bool:
    """
    Basic validation for ChordPro format:
    - Checks that brackets are balanced.
    - Checks that there's at least one chord (e.g., [A], [Dm], etc.) in the text.
    """
    # Balanced brackets: the count of '[' and ']' should be equal
    if text.count('[') != text.count(']'):
        return False
    # At least one chord present (simple regex for [A-G] chord)
    if re.search(r"\[[A-G]", text) is None:
        return False
    return True

# ============================================================================
# HIGH-LEVEL SCRAPING INTERFACE
# ============================================================================

def fetch_song_chords(title: str, artist: str = None, debug: bool = False) -> str:
    """
    High-level function to fetch ChordPro-formatted chords for a given song.
    
    Args:
        title: Song title to search for
        artist: Optional artist name for more specific search
        debug: Enable debug logging if True
        
    Returns:
        str: File path of saved song, or None if not found
        
    Process:
        1. Checks local storage first
        2. Tries Ultimate Guitar, Chordie, and GuitarSongDownload in order
        3. Converts to ChordPro format if needed
        4. Saves to file and optionally commits to git
    """
    if debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode is ON.")
    # 1. Local search
    local_path = find_local_song(title, artist)
    if local_path:
        return os.path.abspath(local_path)
    # 2. Web scrape from sources
    chord_text = None
    # Try Ultimate Guitar first:contentReference[oaicite:6]{index=6}
    chord_text = scrape_from_ultimate_guitar(title, artist)
    source_used = "Ultimate Guitar"
    # If not found on UG, try Chordie
    if not chord_text:
        chord_text = scrape_from_chordie(title, artist)
        source_used = "Chordie"
    # If still not found, try GuitarSongDownload
    if not chord_text:
        chord_text = scrape_from_guitarsongdownload(title, artist)
        source_used = "GuitarSongDownload"
    if not chord_text:
        logger.error(f"Could not find chords for '{title}' from any source.")
        return None
    # 3. Convert to ChordPro format if needed
    chordpro_text = chord_text
    if not validate_chordpro_format(chord_text):
        logger.info(f"Converting chords to ChordPro format (source: {source_used})...")
        chordpro_text = convert_to_chordpro(chord_text)
    # Validate final output
    if not validate_chordpro_format(chordpro_text):
        logger.warning("The fetched song text is not a valid ChordPro format after conversion.")
    # 4. Save to local songs directory
    filename = f"{title}{' - ' + artist if artist else ''}.pro"
    safe_name = filename.replace(os.sep, "_").replace("..", "_")
    save_path = os.path.join(SONGS_DIR, safe_name)
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(chordpro_text.strip() + "\n")
    logger.info(f"Saved chords to {save_path}")
    # 5. Optional: commit to git repository
    if COMMIT_TO_GIT:
        try:
            import subprocess
            subprocess.run(["git", "add", save_path], check=True)
            commit_msg = f"Add chords for {title}{' - ' + artist if artist else ''}"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            logger.info("Committed the new song file to Git repository.")
        except Exception as e:
            logger.error(f"Git commit failed: {e}")
    return os.path.abspath(save_path)

def scrape_song_raw(title: str, artist: str = None) -> str | None:
    """
    Scrape raw chords/lyrics text for a song without saving or validating.
    Tries sources in order: Ultimate Guitar, Chordie, GuitarSongDownload.
    Returns raw text if found, else None.
    """
    try:
        text = scrape_from_ultimate_guitar(title, artist)
        if text:
            return text
    except Exception as e:
        if logger:
            logger.debug(f"UG scrape failed: {e}")

    try:
        text = scrape_from_chordie(title, artist)
        if text:
            return text
    except Exception as e:
        if logger:
            logger.debug(f"Chordie scrape failed: {e}")

    try:
        text = scrape_from_guitarsongdownload(title, artist)
        if text:
            return text
    except Exception as e:
        if logger:
            logger.debug(f"GSD scrape failed: {e}")

    return None
