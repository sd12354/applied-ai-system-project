"""
Apple Music connector.

Reads a library exported from the macOS Music app
(File -> Library -> Export Library...), which is a standard XML property
list. We parse it with Python's built-in ``plistlib`` — no API key, no
paid Apple Developer account, and nothing leaves the machine — so the
whole feature is reproducible by anyone with the exported file.

Why an export instead of the live Apple Music API: the MusicKit API
requires a paid ($99/yr) Apple Developer token, while the Library export
is free and offline. This was the design we chose for exactly that
reason. Spotify is not used because it removed the audio-feature
endpoints a recommender needs for new apps.

Each returned track is a dict: title, artist, genre, play_count.
"""

import plistlib
from typing import List, Dict


def parse_library(xml_path: str) -> List[Dict]:
    """Parse an exported Apple Music Library XML into a list of tracks.

    Only the fields we use are kept. Tracks with no title are skipped;
    a missing play count is treated as 0. Raises FileNotFoundError if the
    path is wrong and ValueError if the file is not a readable plist.
    """
    try:
        with open(xml_path, "rb") as f:
            data = plistlib.load(f)
    except plistlib.InvalidFileException as exc:
        raise ValueError(
            f"{xml_path} is not a valid Apple Music Library export (XML plist)."
        ) from exc

    raw_tracks = data.get("Tracks", {})
    tracks: List[Dict] = []
    for entry in raw_tracks.values():
        title = (entry.get("Name") or "").strip()
        if not title:
            continue
        tracks.append({
            "title": title,
            "artist": (entry.get("Artist") or "Unknown").strip(),
            "genre": (entry.get("Genre") or "").strip(),
            "play_count": int(entry.get("Play Count") or 0),
        })
    return tracks
