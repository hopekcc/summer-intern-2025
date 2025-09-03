"""
Module: chordpro_utils.py

Utilities to validate and convert raw song chord text into ChordPro format.
This module can be used in the song scraping pipeline to ensure chords are in ChordPro format.
Functions:
    is_chordpro(text: str) -> bool
    convert_to_chordpro(text: str) -> str
    process_raw_chords(raw_text: str) -> str
"""
import re

# Regex pattern for a chord token (e.g., "G", "Am", "F#7", "Dmaj7", "G7b9", etc.)
# Covers root note, optional accidentals (# or b), optional quality (maj, min, dim, aug, sus, add, m, M),
# optional numeric extensions (e.g., 7, 9, 11), optional altered extensions (b5, #9, etc.),
# and an optional slash bass note.
CHORD_REGEX_PATTERN = r'[A-G](?:#|b)?' \
                     r'(?:(?:maj|min|dim|aug|sus|add)|m|M)?' \
                     r'\d*(?:[b#]\d+)*' \
                     r'(?:/[A-G](?:#|b)?)?'
# Compile regex for full match of a chord token
CHORD_FULL_REGEX = re.compile(r'^' + CHORD_REGEX_PATTERN + r'$')
# Regex to find chord tokens in a line (including "N.C." or "NC" as a no-chord marker)
CHORD_FINDER_REGEX = re.compile(rf'({CHORD_REGEX_PATTERN}|N\.?C\.?)')


def cleanup_chordpro(text: str) -> str:
    """
    Post-process converted text to make it pass ChordPro validation.
    - Normalize section headers like [Verse 1], [Chorus], [Intro] into {start_of_*} or {comment: ...}
    - Remove trailing chord diagrams (lines like 'D xx0232')
    - Fix dangling brackets
    """
    lines = text.splitlines()
    output = []
    for line in lines:
        stripped = line.strip()

        # Normalize section headers
        if stripped.startswith("[") and stripped.endswith("]"):
            inner = stripped[1:-1].strip().lower()
            if inner.startswith("verse"):
                output.append("{start_of_verse}")
                continue
            elif inner.startswith("chorus"):
                output.append("{start_of_chorus}")
                continue
            elif inner.startswith("bridge"):
                output.append("{start_of_bridge}")
                continue
            elif inner in ("intro", "outro", "solo", "interlude"):
                output.append(f"{{comment: {inner.title()}}}")
                continue
            else:
                output.append(f"{{comment: {inner}}}")
                continue

        # Drop chord diagrams (lines with chord name + fret numbers)
        if re.match(r"^[A-G][#b]?(m|maj|min|dim|aug|sus|add)?\d*\s+[x0-9]{3,}", stripped):
            continue

        # Fix dangling [ without ]
        if stripped.count("[") > stripped.count("]"):
            stripped += "]"
        if stripped.count("]") > stripped.count("["):
            stripped = "[" + stripped

        output.append(stripped)

    return "\n".join(output)


def is_chord_token(token: str) -> bool:
    """Determine if a single token is a chord name (or no-chord marker like N.C.)."""
    t = token.strip()
    if t == "":
        return False
    # Handle common no-chord markers
    if t.upper() in ("NC", "N.C", "N.C."):
        return True
    # Remove trailing punctuation that might follow a chord in raw text (commas, colons, etc.)
    if t[-1] in (",", ";", ":"):
        t = t[:-1]
        if t == "":  # token was just punctuation
            return False
    # Match against chord regex pattern
    return bool(CHORD_FULL_REGEX.match(t))

def is_chord_line(line: str) -> bool:
    """Return True if the line consists of chord tokens (and no lyric words)."""
    if line.strip() == "":
        return False
    tokens = line.split()
    found_chord = False
    for token in tokens:
        if token == "":
            continue
        if is_chord_token(token):
            found_chord = True
        else:
            # Any non-chord token (likely lyric or other text) means this is not a pure chord line
            return False
    return found_chord

def is_lyric_line(line: str) -> bool:
    """Return True if the line contains lyric text (non-chord words)."""
    if line.strip() == "":
        return False
    # A lyric line is not a chord-only line and not a section header in [brackets]
    if is_chord_line(line):
        return False
    if line.strip().startswith("[") and line.strip().endswith("]"):
        return False
    return True

def is_chordpro(text: str) -> bool:
    """Check if the given text appears to be valid ChordPro format.
    
    Criteria:
      - Balanced square brackets (ignoring content in {comment: ...} or {define: ...} lines).
      - Contains at least one chord symbol in square brackets.
      - No lines with chords above lyrics (chords should be inline with lyrics).
      - No section labels like [Intro], [Verse 1], etc., unless converted to ChordPro directives.
    """
    lines = text.splitlines()

    # Filter out {comment: ...} and {define: ...} lines for bracket validation
    filtered_lines = [
        line for line in lines
        if not line.strip().startswith("{comment:") and not line.strip().startswith("{define:")
    ]
    filtered_text = "\n".join(filtered_lines)

    # Check balanced [ and ] brackets
    open_count = 0
    for char in filtered_text:
        if char == '[':
            open_count += 1
        elif char == ']':
            if open_count == 0:
                return False  # found a ']' before a matching '['
            open_count -= 1
    if open_count != 0:
        return False  # unmatched '[' remaining

    # Ensure at least one chord [ ] is present
    has_chord = False
    for match in re.finditer(r'\[([^\]]+)\]', filtered_text):
        inner = match.group(1)
        if is_chord_token(inner):
            has_chord = True
            break
    if not has_chord:
        return False

    # Reject any unconverted section labels in square brackets
    for line in filtered_lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            inner = stripped[1:-1].strip()
            if inner != "" and not is_chord_token(inner):
                # e.g. "Verse 1", "Chorus", "Intro" inside []
                return False

    # Check for chords-over-lyrics pattern
    for i in range(len(filtered_lines) - 1):
        if is_chord_line(filtered_lines[i]) and is_lyric_line(filtered_lines[i + 1]):
            return False

    # Allow at most 2 standalone chord lines
    chord_line_count = sum(1 for line in filtered_lines if is_chord_line(line))
    if chord_line_count > 2:
        return False

    return True

def merge_chords_and_lyrics(chords_line: str, lyrics_line: str) -> str:
    """Merge a chords line with the following lyrics line into one line with inline [chord] tags."""
    if lyrics_line is None:
        lyrics_line = ""
    result = lyrics_line  # start with the lyric line text
    # Find chord tokens and their positions in the chords line
    chord_matches = list(CHORD_FINDER_REGEX.finditer(chords_line))
    if not chord_matches:
        return lyrics_line
    # Pad lyrics line with spaces if needed to accommodate far-right chords
    max_pos = max(m.start(1) for m in chord_matches)
    if max_pos >= len(result):
        result += " " * (max_pos - len(result))
    # Insert chords from rightmost to leftmost to avoid index shifts
    for match in reversed(chord_matches):
        chord_text = match.group(1)
        insert_idx = match.start(1)
        # If insertion index lands on spaces, move to the next lyric character
        if insert_idx < len(result):
            while insert_idx < len(result) and result[insert_idx].isspace():
                insert_idx += 1
        else:
            insert_idx = len(result)
        # Ensure chord is wrapped in [ ] brackets
        if not chord_text.startswith("["):
            chord_text = f"[{chord_text}]"
        # Insert chord text into the lyric line
        result = result[:insert_idx] + chord_text + result[insert_idx:]
    return result

def convert_to_chordpro(text: str) -> str:
    """Convert raw chords/lyrics text to ChordPro format.
    
    - Chords above lyrics are merged into lyrics lines as inline [chord] tags.
    - Section headers [Verse], [Chorus], [Bridge], [Intro] are converted to ChordPro directives.
    - Trailing chord definitions or diagrams are left untouched.
    
    Returns the converted text in ChordPro format.
    """
    lines = text.splitlines()
    output_lines: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Convert section labels in square brackets to ChordPro directives
        if stripped.startswith("[") and stripped.endswith("]") and stripped not in ("[", "[]"):
            inner = stripped[1:-1].strip()
            if inner != "" and not is_chord_token(inner):
                inner_lower = inner.lower()
                if "pre" in inner_lower and "chorus" in inner_lower:
                    output_lines.append(f"{{comment: {inner}}}")
                elif inner_lower.startswith("verse"):
                    output_lines.append("{start_of_verse}")
                elif inner_lower.startswith("chorus"):
                    output_lines.append("{start_of_chorus}")
                elif inner_lower.startswith("bridge"):
                    output_lines.append("{start_of_bridge}")
                elif inner_lower in ("intro", "outro", "solo", "interlude", "instrumental"):
                    output_lines.append(f"{{comment: {inner}}}")
                else:
                    output_lines.append(f"{{comment: {inner}}}")
                i += 1
                continue
        # If this is a chords line followed by a lyrics line, merge them
        if is_chord_line(line) and (i + 1) < len(lines) and is_lyric_line(lines[i + 1]):
            merged = merge_chords_and_lyrics(line, lines[i + 1])
            output_lines.append(merged)
            i += 2  # skip the next line (already merged)
            continue
        # If this is a standalone chords line (no lyric line after), just bracket the chords
        if is_chord_line(line):
            tokens = [tok for tok in line.split() if tok != ""]
            bracketed = [f"[{tok}]" if not (tok.startswith("[") and tok.endswith("]")) else tok for tok in tokens]
            output_lines.append(" ".join(bracketed))
            i += 1
            continue
        # Otherwise, output the line unchanged (lyrics or other text)
        output_lines.append(line)
        i += 1
    return "\n".join(output_lines)

def process_raw_chords(raw_text: str) -> str:
    if is_chordpro(raw_text):
        return raw_text
    converted = convert_to_chordpro(raw_text)
    cleaned = cleanup_chordpro(converted)   # <-- new step
    return cleaned

