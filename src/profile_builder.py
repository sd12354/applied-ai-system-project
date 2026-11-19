"""
Profile builder: Apple Music listening history -> UserProfile.

Takes the tracks parsed from an Apple Music library export and infers a
taste profile, so the user's real library drives the recommendation
instead of a hand-typed request. Genres are weighted by play count, so
the music you actually listen to counts most.

The export only carries genre and play count (not energy or mood), so we
infer target energy from our own catalog (the average energy of songs in
the user's top genre) and leave mood unspecified. That gap is documented
in the model card.
"""

from typing import List, Dict, Tuple
import statistics

from src.recommender import UserProfile
from src.planner import Plan

# Apple Music genre labels -> our catalog genres. Checked in order, as a
# case-insensitive substring match, so more specific labels win.
GENRE_MAP: List[Tuple[Tuple[str, ...], str]] = [
    (("metal",), "metal"),
    (("hip-hop", "hip hop", "rap"), "hip hop"),
    (("r&b", "rnb", "soul"), "r&b"),
    (("jazz",), "jazz"),
    (("country", "americana"), "country"),
    (("ambient", "new age"), "ambient"),
    (("synth", "electronic", "dance", "edm", "house"), "synthwave"),
    (("lo-fi", "lofi", "chillhop"), "lofi"),
    (("alternative", "indie"), "indie pop"),
    (("rock",), "rock"),
    (("pop",), "pop"),
]

ACOUSTIC_GENRES = {"jazz", "ambient", "country"}


def map_genre(apple_genre: str):
    """Map an Apple Music genre label onto a catalog genre, or None."""
    text = (apple_genre or "").lower()
    for keywords, catalog_genre in GENRE_MAP:
        if any(k in text for k in keywords):
            return catalog_genre
    return None


def _genre_energy_means(songs: List[Dict]) -> Dict[str, float]:
    """Average energy of catalog songs per genre (used to fill in uploads)."""
    buckets: Dict[str, List[float]] = {}
    for s in songs:
        buckets.setdefault(s["genre"], []).append(s["energy"])
    return {g: round(statistics.mean(v), 2) for g, v in buckets.items()}


def genre_breakdown(tracks: List[Dict]) -> List:
    """Return [(catalog_genre, total_plays)] for a library, most played first."""
    tally: Dict[str, int] = {}
    for t in tracks:
        genre = map_genre(t.get("genre", ""))
        if genre:
            tally[genre] = tally.get(genre, 0) + max(0, int(t.get("play_count", 0)))
    return sorted(tally.items(), key=lambda kv: kv[1], reverse=True)


def library_candidate_songs(tracks: List[Dict], songs: List[Dict]) -> List[Dict]:
    """Turn uploaded tracks into scoreable songs so they can be recommended.

    The export has no energy/mood/acousticness, so we fill energy with the
    catalog average for the track's genre (the best estimate we have),
    leave mood blank, and set acousticness to 0. Each song is tagged
    ``source="library"`` so the UI can mark it as one of the user's own.
    """
    means = _genre_energy_means(songs)
    overall = round(statistics.mean([s["energy"] for s in songs]), 2) if songs else 0.6
    candidates: List[Dict] = []
    for i, t in enumerate(tracks):
        genre = map_genre(t.get("genre", ""))
        if not genre:
            continue  # can't place an unknown genre in the scoring space
        candidates.append({
            "id": -(i + 1),
            "title": t.get("title", "Unknown"),
            "artist": t.get("artist", "Unknown"),
            "genre": genre,
            "mood": "",
            "energy": means.get(genre, overall),
            "valence": 0.0,
            "danceability": 0.0,
            "acousticness": 0.0,
            "play_count": int(t.get("play_count", 0)),
            "source": "library",
        })
    return candidates


def build_plan_from_library(tracks: List[Dict], songs: List[Dict], k: int = 5) -> Plan:
    """Build a Plan (profile + trace) from parsed Apple Music tracks.

    Returns a Plan so the agent can run it through the same self-checking
    loop it uses for text requests.
    """
    tally: Dict[str, int] = {}
    for t in tracks:
        genre = map_genre(t.get("genre", ""))
        if genre:
            tally[genre] = tally.get(genre, 0) + max(0, int(t.get("play_count", 0)))

    trace: List[str] = [f"Analyzed {len(tracks)} tracks from the Apple Music library."]

    if not tally:
        trace.append("No tracks mapped onto a known genre -> using a neutral profile.")
        profile = UserProfile("", "", 0.6, False)
        return Plan(profile=profile, k=k, trace=trace, recognized=False, energy_specified=False)

    ranked = sorted(tally.items(), key=lambda kv: kv[1], reverse=True)
    favorite_genre = ranked[0][0]
    breakdown = ", ".join(f"{g}={plays}" for g, plays in ranked)
    trace.append(f"Plays by genre: {breakdown}.")
    trace.append(f"Top genre by play count -> '{favorite_genre}'.")

    # Infer target energy from the catalog's songs in that genre.
    energies = [s["energy"] for s in songs if s["genre"] == favorite_genre]
    if energies:
        target_energy = round(statistics.mean(energies), 2)
        trace.append(
            f"Target energy -> {target_energy} (average energy of {favorite_genre} "
            f"songs in the catalog)."
        )
    else:
        target_energy = 0.6
        trace.append("Target energy -> 0.6 (catalog has no songs in that genre).")

    likes_acoustic = favorite_genre in ACOUSTIC_GENRES
    if likes_acoustic:
        trace.append(f"likes_acoustic -> True ('{favorite_genre}' is an acoustic-leaning genre).")

    profile = UserProfile(
        favorite_genre=favorite_genre,
        favorite_mood="",             # the export carries no mood information
        target_energy=target_energy,
        likes_acoustic=likes_acoustic,
    )
    return Plan(profile=profile, k=k, trace=trace, recognized=True, energy_specified=True)
